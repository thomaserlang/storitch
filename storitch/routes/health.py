import aiofiles
import aiofiles.os
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from .. import config

router = APIRouter()


@router.get('/health', response_class=PlainTextResponse)
async def health(response: Response):
    path_exists = await aiofiles.os.path.exists(config.store_path)
    if not path_exists:
        response.status_code = 500
        return 'ERROR - store_path does not exist'
    return 'OK'
