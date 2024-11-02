import logging

from fastapi import APIRouter, HTTPException
from pydicom.errors import InvalidDicomError

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
    try:
        return await get_file_info(
            file_path=store_file.get_file_path(file_id=file_id), filename=filename or ''
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Not found')
    except OSError:
        raise HTTPException(status_code=500, detail='Failed to open file')
    except ValueError:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, does not look like an image'
        )
    except InvalidDicomError:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, could not read file'
        )
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail='Internal server error')