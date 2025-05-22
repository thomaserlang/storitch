import asyncio
import logging
from asyncio import TimerHandle
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response
from fastapi import Path as PathParam
from highdicom.io import ImageFileReader
from pydicom.errors import InvalidDicomError

from storitch.store_file import get_file_path

router = APIRouter(tags=['DICOM'])


@router.get(
    '/{file_id}/dicom/frames/{frames}',
    responses={200: {'content': {'multipart/related': {}}}},
)
async def get_dicom_frames(
    file_id: str,
    frames: Annotated[
        str,
        PathParam(
            description='Comma separated list of frame numbers. 1 based index.',
            examples=['1', '1,2'],
        ),
    ],
):
    frame_numbers = [int(f) for f in frames.split(',')]
    try:
        boundary = str(uuid4())
        return Response(
            content=get_frames(get_file_path(file_id), frame_numbers, boundary),
            headers={
                'Content-Type': f'multipart/related; boundary={boundary}',
            },
        )
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
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail='Internal server error')


def get_frames(path: Path, frames: list[int], boundary: str):
    if path not in _cached:
        _cached[path] = ImageFileReader(path)
        _cached[path].open()
    else:
        if path in _cached_close_callback:
            _cached_close_callback[path].cancel()
    image = _cached[path]

    if _cached[path].number_of_frames > 1:
        _cached_close_callback[path] = asyncio.get_event_loop().call_later(
            60, _close_image, path
        )

    try:
        result = b''
        for frame in frames:
            if frame > image.number_of_frames:
                raise HTTPException(
                    status_code=400, detail=f'Frame {frame} does not exist'
                )
            result += f'--{boundary}\r\n'.encode()
            result += b'Content-Type: application/octet-stream\r\n\r\n'
            result += image.read_frame_raw(frame - 1)
            result += f'\r\n--{boundary}--\r\n'.encode()
        return result
    finally:
        if _cached[path].number_of_frames <= 1:
            _close_image(path)


_cached: dict[Path, ImageFileReader] = {}
_cached_close_callback: dict[Path, TimerHandle] = {}


def _close_image(path: Path):
    if path in _cached:
        _cached[path].close()
        del _cached[path]
    if path in _cached_close_callback:
        _cached_close_callback[path].cancel()
        del _cached_close_callback[path]
