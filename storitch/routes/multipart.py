import asyncio
from typing import Annotated
from fastapi import APIRouter, Security, UploadFile
from ..permanent_store import move_to_permanent_store
from .. import schemas
from ..security import validate_api_key

router = APIRouter()

@router.post("/store", response_model=list[schemas.Upload_result], status_code=201)
async def store(
    file: list[UploadFile],
    api_key: Annotated[str, Security(validate_api_key)],
):
    return await asyncio.gather(
        *[move_to_permanent_store(f, f.filename) for f in file]
    )