import asyncio
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from highdicom.io import ImageFileReader
from pydicom.errors import InvalidDicomError

from storitch.dicom_frame_index import (
    NativeDicomFrameIndex,
    ensure_dicom_frame_index,
    read_native_frame,
)
from storitch.store_file import get_file_path

router = APIRouter(tags=['DICOM'])
_FRAME_SETUP_LOCK = asyncio.Lock()


@router.get(
    '/{file_id}/dicom/frames/{frames}',
    responses={200: {'content': {'multipart/related': {}}}},
)
async def get_dicom_frames_route(
    file_id: str,
    frames: Annotated[
        str,
        PathParam(
            description='Comma separated list of frame numbers. 1 based index.',
            examples=['1', '1,2'],
        ),
    ],
) -> StreamingResponse:
    frame_numbers = [int(f) for f in frames.split(',')]
    try:
        path = get_file_path(file_id)
        async with _FRAME_SETUP_LOCK:
            index = await run_in_threadpool(ensure_dicom_frame_index, path)
            if isinstance(index, NativeDicomFrameIndex):
                return get_indexed_frames(path, index, frame_numbers)
            return await run_in_threadpool(get_frames, path, frame_numbers)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail='Not found') from e
    except OSError as e:
        raise HTTPException(status_code=500, detail='Failed to open file') from e
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, does not look like an image'
        ) from e
    except InvalidDicomError as e:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, could not read file'
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail='Internal server error') from e


_TS_TO_CT = {
    '1.2.840.10008.1.2.4.50': 'image/jpeg',  # JPEG Baseline
    '1.2.840.10008.1.2.4.51': 'image/jpeg',  # JPEG Extended
    '1.2.840.10008.1.2.4.57': 'image/jpeg',  # JPEG Lossless NH
    '1.2.840.10008.1.2.4.70': 'image/jpeg',  # JPEG Lossless
    '1.2.840.10008.1.2.4.80': 'image/jpeg',  # JPEG-LS Lossless
    '1.2.840.10008.1.2.4.81': 'image/jpeg',  # JPEG-LS Near-lossless
    '1.2.840.10008.1.2.4.90': 'image/jp2',  # JPEG 2000 Lossless
    '1.2.840.10008.1.2.4.91': 'image/jp2',  # JPEG 2000
    '1.2.840.10008.1.2.4.201': 'image/jphc',  # HTJ2K Lossless
    '1.2.840.10008.1.2.4.202': 'image/jphc',  # HTJ2K
    '1.2.840.10008.1.2.5': 'application/octet-stream',  # RLE Lossless
}

_BOUNDARY = 'DICOMwebBoundary'


def get_indexed_frames(
    path: Path,
    index: NativeDicomFrameIndex,
    frame_numbers: list[int],
) -> StreamingResponse:
    ts = index.transfer_syntax_uid
    frame_ct = _TS_TO_CT.get(ts, 'application/octet-stream')
    multipart_ct = f'multipart/related; type="{frame_ct}"; boundary={_BOUNDARY}'

    return StreamingResponse(
        _indexed_multipart_stream(path, index, frame_numbers, frame_ct, ts),
        media_type=multipart_ct,
    )


def get_frames(path: Path, frame_numbers: list[int]) -> StreamingResponse:
    reader = ImageFileReader(path)
    reader.__enter__()
    ts = str(reader.transfer_syntax_uid)
    frame_ct = _TS_TO_CT.get(ts, 'application/octet-stream')
    multipart_ct = f'multipart/related; type="{frame_ct}"; boundary={_BOUNDARY}'

    return StreamingResponse(
        _multipart_stream(reader, frame_numbers, frame_ct, ts),
        media_type=multipart_ct,
    )


def _indexed_multipart_stream(
    path: Path,
    index: NativeDicomFrameIndex,
    frame_numbers: list[int],
    ct: str,
    ts: str,
) -> Generator[bytes]:
    header = f'Content-Type: {ct}; transfer-syntax={ts}\r\n\r\n'
    for frame_number in frame_numbers:
        yield f'--{_BOUNDARY}\r\n'.encode()
        yield header.encode()
        yield read_native_frame(path, index, frame_number)
        yield b'\r\n'
    yield f'--{_BOUNDARY}--\r\n'.encode()


def _multipart_stream(
    reader: ImageFileReader,
    frame_numbers: list[int],
    ct: str,
    ts: str,
) -> Generator[bytes]:
    header = f'Content-Type: {ct}; transfer-syntax={ts}\r\n\r\n'
    try:
        for fn in frame_numbers:
            yield f'--{_BOUNDARY}\r\n'.encode()
            yield header.encode()
            yield reader.read_frame_raw(fn - 1)
            yield b'\r\n'
        yield f'--{_BOUNDARY}--\r\n'.encode()
    finally:
        reader.close()
