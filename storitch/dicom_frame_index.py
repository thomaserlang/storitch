import fcntl
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from highdicom.io import ImageFileReader
from pydicom.filereader import read_file_meta_info
from pydicom.uid import UID

from storitch import config

_CACHE_SUFFIX = '@DICOM_FRAME_INDEX'
DICOM_FRAME_INDEX_LOCK_SUFFIX = '.DICOM_FRAME_INDEX_LOCK'
_BUILD_LOCK = Lock()


@dataclass(frozen=True, slots=True)
class NativeDicomFrameIndex:
    transfer_syntax_uid: str
    first_frame_offset: int
    bytes_per_frame: int
    number_of_frames: int


def ensure_dicom_frame_index(path: Path) -> NativeDicomFrameIndex | None:
    cache_path = Path(f'{path}{_CACHE_SUFFIX}')
    if index := _read_index(cache_path):
        return index

    transfer_syntax_uid = UID(read_file_meta_info(str(path)).TransferSyntaxUID)
    if transfer_syntax_uid.is_encapsulated:
        return None

    with _BUILD_LOCK:
        if index := _read_index(cache_path):
            return index

        lock_path = Path(f'{path}{DICOM_FRAME_INDEX_LOCK_SUFFIX}')
        with lock_path.open('a+b') as lock_file:
            fcntl.lockf(lock_file.fileno(), fcntl.LOCK_EX)
            if index := _read_index(cache_path):
                return index

            index = _build_index(path, transfer_syntax_uid)
            if index:
                _write_index(cache_path, index)
            return index


def read_native_frame(
    path: Path,
    index: NativeDicomFrameIndex,
    frame_number: int,
) -> bytes:
    if frame_number < 1 or frame_number > index.number_of_frames:
        raise ValueError(
            f'Frame number must be between 1 and {index.number_of_frames}.'
        )

    descriptor = os.open(path, os.O_RDONLY)
    try:
        data = os.pread(
            descriptor,
            index.bytes_per_frame,
            index.first_frame_offset + ((frame_number - 1) * index.bytes_per_frame),
        )
    finally:
        os.close(descriptor)

    if len(data) != index.bytes_per_frame:
        raise OSError(f'Failed to read frame #{frame_number}.')
    return data


def _build_index(
    path: Path,
    transfer_syntax_uid: UID,
) -> NativeDicomFrameIndex | None:
    with ImageFileReader(path) as reader:
        if reader.transfer_syntax_uid != transfer_syntax_uid:
            raise ValueError(
                'DICOM transfer syntax changed while building frame index.'
            )

        bytes_per_frame = int(reader._bytes_per_frame_uncompressed)
        offsets = tuple(int(value) for value in reader._offset_table)
        expected_offsets = tuple(
            index * bytes_per_frame for index in range(len(offsets))
        )
        if offsets != expected_offsets:
            return None

        return NativeDicomFrameIndex(
            transfer_syntax_uid=str(transfer_syntax_uid),
            first_frame_offset=int(reader._first_frame_offset),
            bytes_per_frame=bytes_per_frame,
            number_of_frames=len(offsets),
        )


def _read_index(path: Path) -> NativeDicomFrameIndex | None:
    try:
        transfer_syntax_uid, offset, frame_size, frame_count = (
            path.read_text().splitlines()
        )
        index = NativeDicomFrameIndex(
            transfer_syntax_uid=transfer_syntax_uid,
            first_frame_offset=int(offset),
            bytes_per_frame=int(frame_size),
            number_of_frames=int(frame_count),
        )
        if (
            index.first_frame_offset < 0
            or index.bytes_per_frame < 1
            or index.number_of_frames < 1
        ):
            return None
        return index
    except (OSError, UnicodeError, ValueError):
        return None


def _write_index(path: Path, index: NativeDicomFrameIndex) -> None:
    path.write_text(
        '\n'.join(
            (
                index.transfer_syntax_uid,
                str(index.first_frame_offset),
                str(index.bytes_per_frame),
                str(index.number_of_frames),
            )
        )
    )
    path.chmod(int(config.file_mode, 8))
