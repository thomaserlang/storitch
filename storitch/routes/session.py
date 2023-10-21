import json
import aiofiles
import uuid
import os
from aiofiles import os as aioos
from typing import Annotated, Literal
from fastapi import APIRouter, Security, Header, Request, HTTPException
from starlette.concurrency import run_in_threadpool
from ..permanent_store import create_store_folder, get_store_folder, upload_result
from .. import schemas, utils
from ..security import validate_api_key
from .. import config

router = APIRouter()


@router.post("/store/session", 
    response_model=schemas.Session_result | schemas.Upload_result, 
    status_code=201,
    description='''
Specify header X-Storitch header with a JSON encoded string to start a session upload:
    
    {
        "filename": "filename.txt",
        "finished": false
    }

For chunked uploads, finished should be false for all but the last chunk.

The response will contain a session ID that should be used for subsequent chunks.
'''
)
async def session_upload_start(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    x_storitch: Annotated[str, Header(description='JSON encoded string')],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
):
    try:
        info = schemas.Session_upload_start.model_validate(json.loads(x_storitch))
    except json.decoder.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON in X-Storitch header')    
    
    file_id = str(uuid.uuid4())    
    return await save(request, file_id, info.filename, info.finished, True)


@router.patch("/store/session", 
    response_model=schemas.Upload_result | schemas.Session_result, 
    status_code=200,
    description='''
Specify header X-Storitch header with a JSON encoded string to continue a session upload:
    
    {
        "session": "session_id",
        "filename": "filename.txt",
        "finished": false
    }

`finished` should be false for all but the last chunk.

When finished, the response will contain the file_id of the file.
'''
)
async def session_upload_append(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    x_storitch: Annotated[str, Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
):
    try:
        info = schemas.Session_upload_append.model_validate(json.loads(x_storitch))
    except json.decoder.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON in X-Storitch header')    

    return await save(request, info.session, info.filename, info.finished, False)


async def save(request: Request, file_id: str, filename: str, finished: bool, new: bool):
    temp_path = os.path.join(
        config.temp_path,
        file_id,
    )
    if new:
        await create_store_folder(file_id)
    async with aiofiles.open(temp_path, mode='wb' if new else 'ab') as f:
        async for chunk in request.stream():
            await f.write(chunk)
    if finished:
        hash_ = await run_in_threadpool(utils.file_sha256, temp_path)
        await aioos.rename(
            temp_path,
            os.path.join(get_store_folder(file_id), file_id),
        )
        return await upload_result(file_id, hash_, filename)
    return schemas.Session_result(session=file_id)