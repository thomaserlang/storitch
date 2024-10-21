from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path, Response
from fastapi.concurrency import run_in_threadpool
from highdicom.io import ImageFileReader

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
        data = await run_in_threadpool(
            get_frames, store_file.get_file_path(file_id), frame_numbers
        )
        return Response(content=data, media_type='multipart/related')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Not found')
    except OSError:
        raise HTTPException(status_code=500, detail='Failed to open file')
    except ValueError:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, does not look like an image'
        )


def get_frames(path: str, frames: list[int]):
    uuid = str(uuid4())
    result = b''
    with ImageFileReader(path) as image:
        for frame in frames:
            boundary = f'{uuid}.{frame}'
            result += f'--{boundary}\r\n'.encode()
            result += b'Content-Type: application/octet-stream\r\n\r\n'
            result += image.read_frame_raw(frame - 1)
            result += f'\r\n--{boundary}--\r\n'.encode()
    return result
