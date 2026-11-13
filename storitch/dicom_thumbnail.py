from pathlib import Path

import numpy as np
import pyvips
from highdicom.content import ModalityLUTTransformation, VOILUTTransformation
from highdicom.io import ImageFileReader
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.pixels import apply_color_lut, apply_icc_profile, pixel_array

from storitch.atomic_output import atomic_output


def get_dicom_thumbnail(path: Path) -> Path:
    thumbnail_path = get_dicom_thumbnail_path(path)
    if thumbnail_path.exists():
        return thumbnail_path

    thumbnail = _read_thumbnail_image(path)
    thumbnail = thumbnail.thumbnail_image(320, height=320, size='down')
    with atomic_output(thumbnail_path) as temporary_path:
        thumbnail.write_to_file(str(temporary_path))
    return thumbnail_path


def get_dicom_thumbnail_path(path: Path) -> Path:
    return path.with_name(f'{path.name}@dicom-thumbnail.webp')


def _read_thumbnail_image(path: Path) -> pyvips.Image:
    # The frame reader avoids Image's volume indexes and large IOD dictionaries.
    with ImageFileReader(path) as reader:
        frame_index = reader.number_of_frames // 2
        metadata = reader.metadata
        # pydicom 3.0.2 misreads 1-bit frames that span byte boundaries.
        if reader.transfer_syntax_uid.is_encapsulated or metadata.BitsAllocated == 1:
            pixels = reader.read_frame(frame_index, correct_color=False)
        else:
            # Read just this frame, avoiding copies of its uncompressed buffer.
            pixels = pixel_array(path, index=frame_index, view_only=True)
        metadata.file_meta = FileMetaDataset()
        metadata.file_meta.TransferSyntaxUID = reader.transfer_syntax_uid

    scale = None
    if metadata.PhotometricInterpretation in ('MONOCHROME1', 'MONOCHROME2'):
        metadata = _frame_metadata(metadata, frame_index)
        if metadata.get('ModalityLUTSequence'):
            pixels = _apply_lut(pixels, metadata.ModalityLUTSequence[0], metadata)
        elif 'RescaleSlope' in metadata and 'RescaleIntercept' in metadata:
            rescale = ModalityLUTTransformation(
                rescale_slope=metadata.RescaleSlope,
                rescale_intercept=metadata.RescaleIntercept,
                rescale_type=metadata.get('RescaleType', 'US'),
            )
            pixels = rescale.apply(pixels, dtype='float32')
        if metadata.get('VOILUTSequence'):
            pixels = _apply_lut(pixels, metadata.VOILUTSequence[0], metadata).astype(
                'float32'
            )
            bits = metadata.VOILUTSequence[0].LUTDescriptor[2]
            pixels *= 255 / (2**bits - 1)
        elif 'WindowCenter' in metadata and 'WindowWidth' in metadata:
            window = VOILUTTransformation(
                window_center=metadata.WindowCenter,
                window_width=metadata.WindowWidth,
                voi_lut_function=metadata.get('VOILUTFunction', 'LINEAR'),
            )
            pixels = window.apply(pixels, output_range=(0, 255), dtype='float32')
        else:
            pixels = pixels.astype('float32')
            minimum, maximum = pixels.min(), pixels.max()
            pixels -= minimum
            if maximum > minimum:
                pixels *= 255 / (maximum - minimum)
        default_shape = (
            'INVERSE'
            if metadata.PhotometricInterpretation == 'MONOCHROME1'
            else 'IDENTITY'
        )
        if metadata.get('PresentationLUTShape', default_shape) == 'INVERSE':
            pixels = 255 - pixels
    elif metadata.PhotometricInterpretation == 'PALETTE COLOR':
        pixels = _apply_palette_lut(pixels, metadata)
    elif metadata.BitsStored > 8:
        scale = float(np.float32(255 / (2**metadata.BitsStored - 1)))

    image = _vips_image(pixels)
    if scale is not None:
        image = image.cast('float').linear([scale], [0])
    image = image.cast('uchar')
    if image.bands > 1 and metadata.get('ICCProfile'):
        image = _vips_image(apply_icc_profile(image.numpy(), metadata))
    return image.copy(interpretation='b-w' if image.bands == 1 else 'srgb')


def _frame_metadata(metadata: Dataset, frame_index: int) -> Dataset:
    result = Dataset()
    result.update(metadata)
    result.file_meta = metadata.file_meta
    groups = list(metadata.get('SharedFunctionalGroupsSequence', []))
    if 'PerFrameFunctionalGroupsSequence' in metadata:
        groups.append(metadata.PerFrameFunctionalGroupsSequence[frame_index])
    for group in groups:
        for keyword in ('PixelValueTransformationSequence', 'FrameVOILUTSequence'):
            if sequence := group.get(keyword):
                result.update(sequence[0])
    return result


def _apply_lut(pixels: np.ndarray, lut: Dataset, metadata: Dataset) -> np.ndarray:
    # pydicom 3.0.2 narrows LUT indexes before clipping, which can wrap them.
    # Decode packed/padded data (DICOM PS3.3 C.11.2.1.1), then clip in _lookup.
    values = _lut_data(lut.LUTDescriptor, lut['LUTData'], metadata)
    return _lookup(pixels, values, lut.LUTDescriptor[1])


def _apply_palette_lut(pixels: np.ndarray, metadata: Dataset) -> np.ndarray:
    entries, first_value, bits = metadata.RedPaletteColorLookupTableDescriptor
    if 'SegmentedRedPaletteColorLookupTableData' in metadata:
        # Decode only the palette's domain, not a full image of RGB values.
        values = apply_color_lut(
            np.arange(first_value, first_value + (entries or 65536), dtype='int64'),
            metadata,
        )
    else:
        values = np.stack(
            [
                _lut_data(
                    metadata[f'{color}PaletteColorLookupTableDescriptor'].value,
                    metadata[f'{color}PaletteColorLookupTableData'],
                    metadata,
                )
                for color in ('Red', 'Green', 'Blue')
            ],
            axis=-1,
        )
    # Scale the small table so the lookup produces 8-bit RGB directly.
    if bits > 8:
        values = values.astype('float32')
        values *= 255 / (2**bits - 1)
    return _lookup(pixels, values.clip(0, 255).astype('uint8'), first_value)


def _lookup(pixels: np.ndarray, values: np.ndarray, first_value: int) -> np.ndarray:
    # libvips evaluates the lookup in regions without full-frame index buffers.
    image = _vips_image(pixels)
    lut = _vips_image(values.reshape(1, *values.shape))
    mapped = (image - first_value).maplut(lut)
    return mapped.numpy().reshape((*pixels.shape, *values.shape[1:]))


def _vips_image(pixels: np.ndarray) -> pyvips.Image:
    pixel_dtype = pixels.dtype.newbyteorder('=')
    if pixel_dtype.kind in 'iu' and pixel_dtype.itemsize == 8:
        pixel_dtype = np.dtype('float64')  # libvips has no 64-bit integer format.
    return pyvips.Image.new_from_array(pixels.astype(pixel_dtype, copy=False))


def _lut_data(
    descriptor: list[int], data: DataElement, metadata: Dataset
) -> np.ndarray:
    entries, _, bits = descriptor
    entries = entries or 65536
    if data.VR == 'OW':
        endian = '<' if metadata.file_meta.TransferSyntaxUID.is_little_endian else '>'
        dtype = 'u1' if bits == 8 and len(data.value) < entries * 2 else endian + 'u2'
        return np.frombuffer(data.value, dtype=dtype, count=entries)
    return np.array(data.value, dtype='uint16', ndmin=1)
