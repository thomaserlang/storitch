import json
import uuid
from pathlib import Path
from typing import Annotated, Literal

from aiofile import async_open
from fastapi import APIRouter, Header, HTTPException, Request, Security
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from storitch import config, schemas, utils
from storitch.security import validate_api_key
from storitch.store_file import create_store_folder, upload_result

router = APIRouter(tags=['Session Upload'])


@router.post(
    '/store/session',
    responses={201: {'model': schemas.UploadResult | schemas.SessionResult}},
    status_code=201,
    description="""
For chunked uploads, `X-Finished` should be false for all but the last chunk.

The response will contain a Session ID that should be used for subsequent chunks or the `file_id` if `X-Finished` is true.
""",
)
async def session_upload_start(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
    x_storitch: Annotated[
        str, Header(description='JSON encoded string', deprecated=True)
    ]
    | None = None,
    x_filename: Annotated[str, Header(description='Filename (unicode escaped)')] = '',
    x_finished: Annotated[bool, Header(description='Finished uploading')] = True,
):
    x_filename = x_filename.encode().decode('unicode-escape')
    if x_storitch:
        try:
            info = schemas.SessionUploadStart.model_validate(json.loads(x_storitch))
        except json.decoder.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail='Invalid JSON in X-Storitch header'
            )
    else:
        try:
            info = schemas.SessionUploadStart(
                filename=x_filename,
                finished=x_finished,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())

    session = str(uuid.uuid4())
    return await save(request, session, info.filename, info.finished, True)


@router.patch(
    '/store/session',
    responses={200: {'model': schemas.UploadResult | schemas.SessionResult}},
    status_code=200,
    description="""
`X-Finished` should be false for all but the last chunk.

When finished, the response will contain the file_id of the file.
""",
)
async def session_upload_append(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
    x_storitch: Annotated[str | None, Header(deprecated=True)] = None,
    x_filename: Annotated[str, Header(description='Filename (unicode escaped)')] = '',
    x_session: Annotated[str, Header(description='Upload Session ID')] = '',
    x_finished: Annotated[bool, Header(description='Finished uploading')] = True,
):
    x_filename = x_filename.encode().decode('unicode-escape')
    if x_storitch:
        try:
            info = schemas.SessionUploadAppend.model_validate(json.loads(x_storitch))
        except json.decoder.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail='Invalid JSON in X-Storitch header'
            )
    else:
        try:
            info = schemas.SessionUploadAppend(
                session=x_session,
                filename=x_filename,
                finished=x_finished,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())

    return await save(request, info.session, info.filename, info.finished, False)


async def save(
    request: Request, session: str, filename: str, finished: bool, new: bool
):
    temp_path = Path(config.temp_path) / session
    if not new and not temp_path.exists():
        raise HTTPException(status_code=400, detail='Upload session not found')
    chunk_count = 0
    async with async_open(temp_path, mode='wb' if new else 'ab') as f:
        async for chunk in request.stream():
            await f.write(chunk)
            chunk_count += 1
            if chunk_count % 30 == 0:
                # Fixes NFS issue with: `Errno 5 Input/output error`
                # It started happening after a system upgrade and python upgrade
                # Not sure why, tested with 100 and it failed, 50 worked so 30 seems safe
                await f.flush()
    if finished:
        hash_ = await run_in_threadpool(utils.file_sha256, temp_path)
        file_id = str(uuid.uuid4())
        path = await create_store_folder(file_id) / file_id
        await run_in_threadpool(temp_path.rename, path)
        path.chmod(int(config.file_mode, 8))
        return await upload_result(file_id, hash_, filename)
    return schemas.SessionResult(session=session)
