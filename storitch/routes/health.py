from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from storitch import config

router = APIRouter()


@router.get('/health', response_class=PlainTextResponse)
async def health(response: Response):
    if not config.store_path.exists():
        response.status_code = 500
        return 'ERROR - store_path does not exist'
    return 'OK'
