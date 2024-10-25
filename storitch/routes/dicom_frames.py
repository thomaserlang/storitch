import asyncio
from asyncio import TimerHandle
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path, Response
from highdicom.io import ImageFileReader
from pydicom.errors import InvalidDicomError

from storitch import store_file

router = APIRouter(tags=['DICOM'])


@router.get(
    '/{file_id}/dicom/frames/{frames}',
    responses={200: {'content': {'multipart/related': {}}}},
)
async def get_dicom_frames(
    file_id: str,
    frames: Annotated[
        str,
        Path(
            description='Comma separated list of frame numbers. 1 based index.',
            example='1,2',
        ),
    ],
):
    frame_numbers = [int(f) for f in frames.split(',')]
    try:
        data = get_frames(store_file.get_file_path(file_id), frame_numbers)
        return Response(content=data, media_type='multipart/related')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Not found')
    except OSError:
        raise HTTPException(status_code=500, detail='Failed to open file')
    except ValueError:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, does not look like an image'
        )
    except InvalidDicomError:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, could not read file'
        )


def get_frames(path: str, frames: list[int]):
    if path not in _cached:
        _cached[path] = ImageFileReader(path)
        _cached[path].open()
    else:
        _cached_close_callback[path].cancel()
    image = _cached[path]

    if _cached[path].number_of_frames > 1:
        _cached_close_callback[path] = loop.call_later(1, _close_image, path)

    uuid = str(uuid4())
    result = b''

    try:
        for frame in frames:
            boundary = f'{uuid}.{frame}'
            result += f'--{boundary}\r\n'.encode()
            result += b'Content-Type: application/octet-stream\r\n\r\n'
            result += image.read_frame_raw(frame - 1)
            result += f'\r\n--{boundary}--\r\n'.encode()
    finally:
        if _cached[path].number_of_frames == 1:
            _close_image(path)

    return result


_cached: dict[str, ImageFileReader] = {}
_cached_close_callback: dict[str, TimerHandle] = {}
loop = asyncio.get_event_loop()


def _close_image(path: str):
    if path in _cached:
        _cached[path].close()
        del _cached[path]
    if path in _cached_close_callback:
        _cached_close_callback[path].cancel()
        del _cached_close_callback[path]
