import json
import aiofiles
import uuid
import os
from aiofiles import os as aioos
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Header, Request, HTTPException
from starlette.concurrency import run_in_threadpool
from ..permanent_store import create_store_folder, get_store_folder, upload_result
from .. import schemas, utils
from ..security import validate_api_key

router = APIRouter()


@router.post("/store/session", response_model=schemas.Upload_result | schemas.Session_result, status_code=201)
async def session_upload_start(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    x_storitch: Annotated[str, Header()],
    request: Request,
    api_key = Depends(validate_api_key),
):
    try:
        info = schemas.Session_upload_start.parse_obj(json.loads(x_storitch))
    except json.decoder.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON in X-Storitch header')    
    
    file_id = str(uuid.uuid4())    
    return await save(request, file_id, info.filename, info.finished, True)


@router.patch("/store/session", response_model=schemas.Upload_result | schemas.Session_result, status_code=200)
async def session_upload_append(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    x_storitch: Annotated[str, Header()],
    request: Request,
    api_key = Depends(validate_api_key),
):
    try:
        info = schemas.Session_upload_append.parse_obj(json.loads(x_storitch))
    except json.decoder.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON in X-Storitch header')    

    return await save(request, info.session, info.filename, info.finished, False)


async def save(request: Request, file_id: str, filename: str, finished: bool, new: bool):
    path = os.path.join(
        get_store_folder(file_id),
        f'{file_id}_temp',
    )
    if new:
        await create_store_folder(file_id)
    async with aiofiles.open(path, mode='wb' if new else 'ab') as f:
        async for chunk in request.stream():
            await f.write(chunk)
    if finished:
        hash_ = await run_in_threadpool(utils.file_sha256, path)
        await aioos.rename(path, path[:-len('_temp')])
        return await upload_result(file_id, hash_, filename)
    return schemas.Session_result(session=file_id)