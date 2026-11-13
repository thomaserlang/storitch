import base64
import json
import shutil
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
    status_code=201,
    description="""
For chunked uploads, `X-Finished` should be false for all but the last chunk.

The response will contain a Session ID that should be used for subsequent 
chunks or the `file_id` if `X-Finished` is true.
""",
)
async def session_upload_start_route(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
    x_storitch: Annotated[
        str, Header(description='JSON encoded string', deprecated=True)
    ]
    | None = None,
    x_filename: Annotated[str, Header(description='Filename (unicode escaped)')] = '',
    x_finished: Annotated[bool, Header(description='Finished uploading')] = True,
    x_checksum_crc32c: Annotated[
        schemas.CRC32C | None,
        Header(description='Base64 whole-file CRC32C; final request only'),
    ] = None,
) -> schemas.UploadResult | schemas.SessionResult:
    x_filename = x_filename.encode().decode('unicode-escape')
    if x_storitch:
        try:
            info = schemas.SessionUploadStart.model_validate(json.loads(x_storitch))
        except json.decoder.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail='Invalid JSON in X-Storitch header'
            ) from e
    else:
        try:
            info = schemas.SessionUploadStart(
                filename=x_filename,
                finished=x_finished,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors()) from e

    session = str(uuid.uuid4())
    return await save(
        request, session, info.filename, info.finished, True, x_checksum_crc32c
    )


@router.patch(
    '/store/session',
    responses={200: {'model': schemas.UploadResult | schemas.SessionResult}},
    status_code=200,
    description="""
`X-Finished` should be false for all but the last chunk.

When finished, the response will contain the file_id of the file.
""",
)
async def session_upload_append_route(
    content_type: Annotated[Literal['application/octet-stream'], Header()],
    request: Request,
    api_key: Annotated[str, Security(validate_api_key)],
    x_storitch: Annotated[str | None, Header(deprecated=True)] = None,
    x_filename: Annotated[str, Header(description='Filename (unicode escaped)')] = '',
    x_session: Annotated[str, Header(description='Upload Session ID')] = '',
    x_finished: Annotated[bool, Header(description='Finished uploading')] = True,
    x_checksum_crc32c: Annotated[
        schemas.CRC32C | None,
        Header(description='Base64 whole-file CRC32C; final request only'),
    ] = None,
) -> schemas.UploadResult | schemas.SessionResult:
    x_filename = x_filename.encode().decode('unicode-escape')
    if x_storitch:
        try:
            info = schemas.SessionUploadAppend.model_validate(json.loads(x_storitch))
        except json.decoder.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail='Invalid JSON in X-Storitch header'
            ) from e
    else:
        try:
            info = schemas.SessionUploadAppend(
                session=x_session,
                filename=x_filename,
                finished=x_finished,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors()) from e

    return await save(
        request, info.session, info.filename, info.finished, False, x_checksum_crc32c
    )


async def save(
    request: Request,
    session: str,
    filename: str,
    finished: bool,
    new: bool,
    expected_crc32c: bytes | None = None,
) -> schemas.UploadResult | schemas.SessionResult:
    if expected_crc32c is not None and not finished:
        raise HTTPException(422, 'X-Checksum-CRC32C is only valid on the final request')
    temp_path = Path(config.temp_path) / session
    if not new and not temp_path.exists():
        raise HTTPException(status_code=400, detail='Upload session not found')
    async with async_open(temp_path, mode='wb' if new else 'ab') as f:
        async for chunk in request.stream():
            await f.write(chunk)
    if finished:
        hash_, crc = await run_in_threadpool(
            utils.file_checksums, temp_path, crc32c=expected_crc32c is not None
        )
        if expected_crc32c is not None and crc != expected_crc32c:
            await run_in_threadpool(temp_path.unlink)
            raise HTTPException(422, detail={'code': 'upload_checksum_mismatch'})
        file_id = hash_ if config.deduplication else str(uuid.uuid4())
        path = await create_store_folder(file_id) / file_id
        if config.deduplication and path.exists():
            temp_path.unlink()
        else:
            await run_in_threadpool(shutil.move, temp_path, path)
            path.chmod(int(config.file_mode, 8))
        result = await upload_result(file_id=file_id, hash_=hash_, filename=filename)
        if crc is not None:
            result.checksum_crc32c = base64.b64encode(crc).decode('ascii')
        return result

    return schemas.SessionResult(session=session)
