import asyncio
import re, os, logging
from aiofiles import os as aioos
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from mimetypes import guess_type
from pydantic import constr
from storitch import config
from .. import permanent_store

router = APIRouter()

description = '''
Download a file from the permanent store.

To resize an image, add the arguments to the path.

Specify the path and add a "@" followed by the arguments.

Arguments can be specified as followed:

    SXx         - Width, keeps aspect ratio
    SYx         - Height, keeps aspect ration. 
                  Ignored if SX is specified.

The file format can be specified by ending the path with
E.g. .jpg, .png, .tiff, etc.

The arguments can be separated with _ or just
don't separate them. Works either way. 

Example:

    /b12ece41-919b-46ef-96b8-703af0f1b5ac@SX1024_ROTATE90.png

Resizes the image to a width of 1024, rotates it 90 degrees and converts 
it to a PNG file.
'''
@router.get('/{file_id}', response_class=FileResponse, description=description)
@router.get('/{file_id}/{filename}', response_class=FileResponse, description=description)
async def download(
    file_id: constr(pattern=r'[a-zA-Z0-9-]+(@[a-zA-Z0-9_-.]+)?'),
    filename: str = None,
):
    path = permanent_store.get_file_path(file_id)
    if '@' in file_id:
        converted = await convert(path)
        if not converted: 
            raise HTTPException(status_code=500, detail='Failed to convert file.')
        path = converted
    try:
        stat = await aioos.stat(path)
        return FileResponse(
            path=path,
            stat_result=stat,
            media_type=guess_type(filename or file_id)[0] or 'application/octet-stream',
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Not found')


async def convert(path: str):
    '''
    Specify the path and add a "@" followed by the arguments.

    This allows us to easily get the original file, make the changes,
    save the file with the full path, so the server never has to do
    the operation again, as long as the arguments are precisely the same.
    '''
    p = path.split('@')
    if len(p) != 2:
        raise HTTPException(status_code=400, detail='Invalid thumbnail arguments.')

    if len(p[1]) > 40:
        raise HTTPException(status_code=400, detail='Parameters too long, max 40.')

    # get the extension from the path
    f = os.path.splitext(path)
    ext = f[1].lower() if len(f) == 2 else ''
    if ext:
        if ext not in config.image_exts:
            raise HTTPException(status_code=400, detail='Invalid file extension.')
    
    args = []
    size = _get_size(p[1], args)
    save_path = f'{p[0]}@{size}{ext}'

    if os.path.exists(save_path):
        return save_path

    # "[0]" is to limit to the first image if e.g. the file is a dicom and contains multiple images
    p = await asyncio.subprocess.create_subprocess_exec(
        'convert',
        f'{p[0]}[0]',
        *args,
        save_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, error = await p.communicate()
    if error:
        logging.error(f'{path}: {str(error.decode())}')
        return
    os.chmod(save_path, int(config.file_mode, 8))
    return save_path


def _get_size(arguments: str, convert_args: list[str]):
    size_match = re.search(
        r'SX([0-9]+)|SY([0-9]+)',
        arguments,
        re.I
    )
    if size_match:
        convert_args.append('-resize')
        if size_match.group(1):
            is_allowed_size(int(size_match.group(1)))
            convert_args.append(f'{size_match.group(1)}x')
            return f'SX{size_match.group(1)}'
        elif size_match.group(2):
            is_allowed_size(int(size_match.group(2)))
            convert_args.append(f'x{size_match.group(2)}')
            return f'SY{size_match.group(2)}'
    return ''


def is_allowed_size(size: int):
    if config.allowed_resizes and size not in config.allowed_resizes:
        raise HTTPException(status_code=400, detail=f'Size {size} not allowed.')
    return True