from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from storitch.dicom_frame_index import (
    DICOM_FRAME_INDEX_LOCK_SUFFIX,
    NativeDicomFrameIndex,
    ensure_dicom_frame_index,
    read_native_frame,
)


def test_native_dicom_frame_index(tmp_path: Path) -> None:
    path = tmp_path / 'content-id'
    frames = (
        bytes(range(12)),
        bytes(range(12, 24)),
        bytes(range(24, 36)),
    )
    _write_native_multiframe_dicom(path, frames)

    index = ensure_dicom_frame_index(path)

    assert isinstance(index, NativeDicomFrameIndex)
    assert Path(f'{path}@DICOM_FRAME_INDEX').is_file()
    assert Path(f'{path}{DICOM_FRAME_INDEX_LOCK_SUFFIX}').is_file()
    assert read_native_frame(path, index, 1) == frames[0]
    assert read_native_frame(path, index, 2) == frames[1]
    assert read_native_frame(path, index, 3) == frames[2]
    assert ensure_dicom_frame_index(path) == index

    Path(f'{path}@DICOM_FRAME_INDEX').unlink()
    with ThreadPoolExecutor(max_workers=8) as executor:
        indexes = list(executor.map(lambda _: ensure_dicom_frame_index(path), range(8)))
    assert indexes == [index] * 8


def _write_native_multiframe_dicom(path: Path, frames: tuple[bytes, ...]) -> None:
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b'\0' * 128)
    dataset.SOPClassUID = CTImageStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.Modality = 'CT'
    dataset.Rows = 2
    dataset.Columns = 3
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = 'MONOCHROME2'
    dataset.BitsAllocated = 16
    dataset.BitsStored = 12
    dataset.HighBit = 11
    dataset.PixelRepresentation = 0
    dataset.NumberOfFrames = len(frames)
    dataset.PixelData = b''.join(frames)
    dataset.save_as(path, enforce_file_format=True)
