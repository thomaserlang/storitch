import asyncio
from fastapi import APIRouter, UploadFile
from ..permanent_store import move_to_permanent_store
from .. import schemas

router = APIRouter()

@router.post("/store", response_model=list[schemas.Upload_result], status_code=201)
async def store(
    file: list[UploadFile],
):
    return await asyncio.gather(
        *[move_to_permanent_store(f, f.filename) for f in file]
    )