import asyncio
import io
import struct
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import pyvips
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient
from PIL import Image
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.filewriter import dcmwrite
from pydicom.pixels import pack_bits, pixel_array
from pydicom.uid import (
    ExplicitVRBigEndian,
    ExplicitVRLittleEndian,
    RLELossless,
    SecondaryCaptureImageStorage,
    generate_uid,
)

from storitch import config
from storitch.dicom_thumbnail import (
    _read_thumbnail_image,
    get_dicom_thumbnail,
    get_dicom_thumbnail_path,
)
from storitch.main import app
from storitch.routes import dicom_thumbnail_routes
from storitch.store_file import get_file_path


def test_dicom_thumbnail_uses_middle_frame_and_caches_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, 'store_path', tmp_path)
    path = get_file_path('test-dicom')
    path.parent.mkdir(parents=True)
    _dicom(path).save_as(path, enforce_file_format=True)
    client = TestClient(app)

    with patch('storitch.dicom_thumbnail.pixel_array', wraps=pixel_array) as decode:
        response = client.get('/test-dicom/dicom/thumbnail')
        cached = client.get('/test-dicom/dicom/thumbnail')

    assert response.status_code == cached.status_code == 200
    assert response.headers['content-type'] == 'image/webp'
    assert cached.content == response.content
    decode.assert_called_once_with(path, index=1, view_only=True)
    with Image.open(io.BytesIO(response.content)) as thumbnail:
        assert thumbnail.size == (3, 2)
        assert list(thumbnail.convert('L').tobytes()) == pytest.approx(
            [0, 51, 102, 153, 204, 255], abs=8
        )


@pytest.mark.parametrize('location', ['top', 'shared', 'per_frame'])
def test_window_and_rescale_metadata(tmp_path: Path, location: str) -> None:
    path = tmp_path / 'dicom'
    dataset = _dicom(path)
    voi = Dataset()
    voi.WindowCenter = 128
    voi.WindowWidth = 256
    if location == 'top':
        dataset.update(voi)
    else:
        group = Dataset()
        group.FrameVOILUTSequence = [voi]
        rescale = Dataset()
        rescale.RescaleSlope = dataset.RescaleSlope
        rescale.RescaleIntercept = dataset.RescaleIntercept
        group.PixelValueTransformationSequence = [rescale]
        del dataset.RescaleSlope
        del dataset.RescaleIntercept
        if location == 'shared':
            dataset.SharedFunctionalGroupsSequence = [group]
        else:
            # Only the selected middle frame has these transformations.
            dataset.PerFrameFunctionalGroupsSequence = [Dataset(), group, Dataset()]
    dataset.save_as(path, enforce_file_format=True)

    np.testing.assert_allclose(
        _read_thumbnail_image(path).numpy(), [[0, 50, 100], [150, 200, 250]], atol=1
    )


def test_monochrome1_inverts_thumbnail(tmp_path: Path) -> None:
    path = tmp_path / 'dicom'
    _dicom(path, inverted=True).save_as(path, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [
        [255, 204, 153],
        [102, 51, 0],
    ]


@pytest.mark.parametrize('encoding', ['US', 'packed', 'padded', '16bit'])
def test_voi_lut_clips_without_wrapping(tmp_path: Path, encoding: str) -> None:
    path = tmp_path / 'dicom'
    dataset = _dicom(path)
    dataset.NumberOfFrames = 1
    del dataset.RescaleSlope
    del dataset.RescaleIntercept
    lut = Dataset()
    bits = 16 if encoding == '16bit' else 8
    lut.LUTDescriptor = [512, 0, bits]
    values = [(i // 2) * (257 if bits == 16 else 1) for i in range(512)]
    if encoding == 'US':
        lut.add_new(0x00283006, 'US', values)
    else:
        lut.LUTData = (
            bytes(values) if encoding == 'packed' else struct.pack('<512H', *values)
        )
    dataset.VOILUTSequence = [lut]
    dataset.PixelData = struct.pack('<6H', 0, 255, 256, 511, 512, 4095)
    dataset.save_as(path, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [
        [0, 127, 128],
        [255, 255, 255],
    ]


@pytest.mark.parametrize('bits', [8, 16])
def test_single_entry_voi_lut(tmp_path: Path, bits: int) -> None:
    path = tmp_path / 'dicom'
    dataset = _dicom(path)
    del dataset.RescaleSlope
    del dataset.RescaleIntercept
    lut = Dataset()
    lut.LUTDescriptor = [1, 0, bits]
    lut.add_new(0x00283006, 'US', 128 if bits == 8 else 128 * 257)
    dataset.VOILUTSequence = [lut]
    dataset.save_as(path, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [[128] * 3] * 2


@pytest.mark.parametrize('first_value', [-100, 100])
def test_voi_lut_clips_signed_pixels(tmp_path: Path, first_value: int) -> None:
    path = tmp_path / 'dicom'
    dataset = _dicom(path)
    dataset.NumberOfFrames = 1
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 1
    del dataset.RescaleSlope
    del dataset.RescaleIntercept
    lut = Dataset()
    lut.LUTDescriptor = [3, first_value, 8]
    lut.add_new(0x00283006, 'US', [0, 127, 255])
    dataset.VOILUTSequence = [lut]
    dataset.PixelData = struct.pack(
        '<6h',
        first_value - 1,
        first_value,
        first_value + 1,
        first_value + 2,
        32767,
        -32768,
    )
    dataset.save_as(path, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [[0, 0, 127], [255, 255, 0]]


def test_voi_lut_after_fractional_rescale(tmp_path: Path) -> None:
    path = tmp_path / 'dicom'
    dataset = _dicom(path)
    dataset.NumberOfFrames = 1
    dataset.RescaleSlope = 0.5
    dataset.RescaleIntercept = -100.5
    lut = Dataset()
    lut.add_new(0x00283002, 'SS', [3, -100, 8])
    lut.add_new(0x00283006, 'US', [0, 127, 255])
    dataset.VOILUTSequence = [lut]
    dataset.PixelData = struct.pack('<6H', 0, 1, 2, 3, 4, 5)
    dataset.save_as(path, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [[0, 0, 0], [127, 127, 255]]


def test_bit_packed_middle_frame(tmp_path: Path) -> None:
    path = tmp_path / 'dicom'
    dataset = _dicom(path)
    dataset.BitsAllocated = dataset.BitsStored = 1
    dataset.HighBit = 0
    del dataset.RescaleSlope
    del dataset.RescaleIntercept
    # Six pixels per frame: the middle frame spans two bytes.
    dataset.PixelData = pack_bits(
        np.array([0] * 6 + [0, 1, 0, 1, 1, 0] + [1] * 6, dtype='uint8')
    )
    dataset.save_as(path, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [[0, 255, 0], [255, 255, 0]]


def test_failed_thumbnail_does_not_publish_cache(tmp_path: Path) -> None:
    path = tmp_path / 'dicom'
    _dicom(path).save_as(path, enforce_file_format=True)
    with patch.object(
        pyvips.Image, 'write_to_file', side_effect=OSError('write failed')
    ):
        with pytest.raises(OSError, match='write failed'):
            get_dicom_thumbnail(path)
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('encoding', ['packed', 'padded', '16le', '16be', 'segmented'])
def test_palette_thumbnail(tmp_path: Path, encoding: str) -> None:
    path = tmp_path / 'palette-dicom'
    dataset = _dicom(path)
    dataset.NumberOfFrames = 1
    dataset.PhotometricInterpretation = 'PALETTE COLOR'
    bits = 8 if encoding in ('packed', 'padded') else 16
    endian = '>' if encoding == '16be' else '<'
    if encoding == '16be':
        dataset.file_meta.TransferSyntaxUID = ExplicitVRBigEndian
    for color in ('Red', 'Green', 'Blue'):
        setattr(dataset, f'{color}PaletteColorLookupTableDescriptor', [512, 0, bits])
        values = [
            (i // 2 if color == 'Red' else 255 - i // 2 if color == 'Blue' else 0)
            * (257 if bits == 16 else 1)
            for i in range(512)
        ]
        keyword = f'{color}PaletteColorLookupTableData'
        if encoding == 'segmented':
            keyword = f'Segmented{keyword}'
            values = [0, len(values), *values]  # One discrete segment.
        data = (
            bytes(values)
            if encoding == 'packed'
            else struct.pack(f'{endian}{len(values)}H', *values)
        )
        setattr(dataset, keyword, data)
    dataset.PixelData = struct.pack(f'{endian}6H', 0, 255, 256, 511, 512, 4095)
    dcmwrite(path, dataset, enforce_file_format=True)

    assert _read_thumbnail_image(path).numpy().tolist() == [
        [[0, 0, 255], [127, 0, 128], [128, 0, 127]],
        [[255, 0, 0], [255, 0, 0], [255, 0, 0]],
    ]


@pytest.mark.parametrize('compressed', [False, True])
@pytest.mark.parametrize('bits', [8, 16])
def test_single_frame_color_thumbnail(
    tmp_path: Path, compressed: bool, bits: int
) -> None:
    path = tmp_path / 'color-dicom'
    dataset = _dicom(path)
    dataset.NumberOfFrames = 1
    dataset.SamplesPerPixel = 3
    dataset.PhotometricInterpretation = 'RGB'
    dataset.PlanarConfiguration = 0
    dataset.BitsAllocated = dataset.BitsStored = bits
    dataset.HighBit = bits - 1
    samples = [value * (257 if bits == 16 else 1) for value in (255, 128, 64)]
    dataset.PixelData = struct.pack('<3H' if bits == 16 else '<3B', *samples) * 6
    if compressed:
        dataset.compress(RLELossless)
    dataset.save_as(path, enforce_file_format=True)
    with Image.open(get_dicom_thumbnail(path)) as thumbnail:
        assert thumbnail.size == (3, 2)
        assert thumbnail.convert('RGB').getpixel((0, 0)) == pytest.approx(
            (255, 128, 64), abs=8
        )


def test_cached_thumbnail_bypasses_render_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, 'store_path', tmp_path)
    cached = get_dicom_thumbnail_path(get_file_path('cached'))
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b'cached-image')

    async def request() -> None:
        lock = asyncio.Lock()
        monkeypatch.setattr(dicom_thumbnail_routes, '_RENDER_LOCK', lock)
        async with (
            lock,
            AsyncClient(
                transport=ASGITransport(app=app), base_url='http://test'
            ) as client,
        ):
            response = await asyncio.wait_for(
                client.get('/cached/dicom/thumbnail'), timeout=2
            )
        assert response.status_code == 200
        assert response.content == b'cached-image'

    asyncio.run(request())


def _dicom(path: Path, *, inverted: bool = False) -> FileDataset:
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    dataset = FileDataset(path, {}, file_meta=meta, preamble=b'\0' * 128)
    dataset.SOPClassUID = meta.MediaStorageSOPClassUID
    dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    dataset.Rows = 2
    dataset.Columns = 3
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = 'MONOCHROME1' if inverted else 'MONOCHROME2'
    dataset.BitsAllocated = 16
    dataset.BitsStored = 12
    dataset.HighBit = 11
    dataset.PixelRepresentation = 0
    dataset.NumberOfFrames = 3
    dataset.RescaleSlope = 2
    dataset.RescaleIntercept = -100
    dataset.PixelData = struct.pack(
        '<18H', *([0] * 6 + [50, 75, 100, 125, 150, 175] + [4095] * 6)
    )
    return dataset
