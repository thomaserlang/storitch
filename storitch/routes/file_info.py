from fastapi import APIRouter

from storitch import store_file
from storitch.identify_file import get_file_info
from storitch.schemas import FileInfo

router = APIRouter(tags=['File info'])

DESCRIPTION = """
    Returns the same file info that you got when the file was uploaded.
"""


@router.get(
    '/file-info/{file_id}',
    name='Get File Info',
    description=DESCRIPTION,
    response_model=FileInfo,
)
@router.get(
    '/file-info/{file_id}/{filename}',
    name='Get File Info with filename',
    description=DESCRIPTION,
    response_model=FileInfo,
)
async def get_file_info_route(
    file_id: str,
    filename: str | None = None,
):
    return await get_file_info(
        file_path=store_file.get_file_path(file_id=file_id), filename=filename or ''
    )
