import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from storitch.dicom_thumbnail import get_dicom_thumbnail, get_dicom_thumbnail_path
from storitch.store_file import get_file_path

router = APIRouter(tags=['DICOM'])
# Serialize expensive renders within a worker; cached thumbnails bypass this.
_RENDER_LOCK = asyncio.Lock()


@router.get('/{file_id}/dicom/thumbnail', response_class=FileResponse)
async def get_dicom_thumbnail_route(file_id: str) -> FileResponse:
    try:
        path = get_file_path(file_id)
        thumbnail_path = get_dicom_thumbnail_path(path)
        if not await run_in_threadpool(thumbnail_path.exists):
            async with _RENDER_LOCK:
                await run_in_threadpool(get_dicom_thumbnail, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail='Not found') from exc
    except Exception as exc:
        logging.exception('Failed to render DICOM thumbnail')
        raise HTTPException(
            status_code=500, detail='Failed to render DICOM thumbnail'
        ) from exc
    return FileResponse(thumbnail_path, media_type='image/webp')
