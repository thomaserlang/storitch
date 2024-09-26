import asyncio
from typing import Annotated

from fastapi import APIRouter, Security, UploadFile

from .. import schemas
from ..security import validate_api_key
from ..store_file import move_to_permanent_store

router = APIRouter()


@router.post('/store', response_model=list[schemas.UploadResult], status_code=201)
async def store(
    file: list[UploadFile],
    api_key: Annotated[str, Security(validate_api_key)],
):
    return await asyncio.gather(
        *[move_to_permanent_store(f, f.filename or '') for f in file]
    )
