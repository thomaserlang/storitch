import json
import aiofiles
import uuid
import os
from aiofiles import os as aioos
from typing import Annotated, Literal
from fastapi import APIRouter, Security, Header, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from ..permanent_store import create_store_folder, upload_result
from .. import schemas, utils
from ..security import validate_api_key
from .. import config

router = APIRouter()


@router.post("/store/session", 
    response_model=schemas.Upload_result | schemas.Session_result, 
    status_code=201,
    description='''
For chunked uploads, `X-Finished` should be false for all but the last chunk.

The response will contain a Session ID that should be used for subsequent chunks or the `file_id` if `X-Finished` is true.
'''
)
async def session_upload_start(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
    x_storitch: Annotated[str, Header(description='JSON encoded string', deprecated=True)] = None,
    x_filename: Annotated[str, Header(description='Filename')] = '',
    x_finished: Annotated[bool, Header(description='Finished uploading')] = True,
):
    if x_storitch:
        try:
            info = schemas.Session_upload_start.model_validate(json.loads(x_storitch))
        except json.decoder.JSONDecodeError:
            raise HTTPException(status_code=400, detail='Invalid JSON in X-Storitch header')
    else:
        try:
            info = schemas.Session_upload_start(
                filename=x_filename,
                finished=x_finished,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())
    
    session = str(uuid.uuid4())    
    return await save(request, session, info.filename, info.finished, True)


@router.patch("/store/session", 
    response_model=schemas.Upload_result | schemas.Session_result, 
    status_code=200,
    description='''
`X-Finished` should be false for all but the last chunk.

When finished, the response will contain the file_id of the file.
'''
)
async def session_upload_append(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
    x_storitch: Annotated[str | None, Header(deprecated=True)] = None,
    x_filename: Annotated[str, Header(description='Filename')] = '',
    x_session: Annotated[str, Header(description='Upload Session ID')] = '',
    x_finished: Annotated[bool, Header(description='Finished uploading')] = True,
):
    if x_storitch:
        try:
            info = schemas.Session_upload_append.model_validate(json.loads(x_storitch))
        except json.decoder.JSONDecodeError:
            raise HTTPException(status_code=400, detail='Invalid JSON in X-Storitch header')
    else:
        try:
            info = schemas.Session_upload_append(
                session=x_session,
                filename=x_filename,
                finished=x_finished,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())

    return await save(request, info.session, info.filename, info.finished, False)


async def save(request: Request, session: str, filename: str, finished: bool, new: bool):
    temp_path = os.path.join(
        config.temp_path,
        session,
    )
    if not new and not await aioos.path.exists(temp_path):
        raise HTTPException(status_code=400, detail='Upload session not found')
    async with aiofiles.open(temp_path, mode='wb' if new else 'ab') as f:
        async for chunk in request.stream():
            await f.write(chunk)
    if finished:
        hash_ = await run_in_threadpool(utils.file_sha256, temp_path)
        file_id = str(uuid.uuid4())
        dir = await create_store_folder(file_id)
        path = os.path.join(dir, file_id)
        await aioos.rename(temp_path, path)
        os.chmod(path, int(config.file_mode, 8))
        return await upload_result(file_id, hash_, filename)
    return schemas.Session_result(session=session)