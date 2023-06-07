from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse
import aiofiles
from .. import config

router = APIRouter()

@router.post("/health", response_class=PlainTextResponse, status_code=200)
async def health(response: Response):
    path_exists = await aiofiles.os.path.exists(config.store_path)
    if not path_exists:
        response.status_code = 500
        return 'ERROR - store_path does not exist'
    return 'OK'