import re, os
import logging
from aiofiles import os as aioos
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from wand import image, exceptions
from .. import permanent_store
from mimetypes import guess_type

router = APIRouter()

@router.get('/{file_id}', response_class=FileResponse)
@router.get('/{file_id}/{filename}', response_class=FileResponse)
async def download(
    file_id: str,
    filename: str = None,
):
    path = permanent_store.get_file_path(file_id)
    if '@' in file_id:
        if not await run_in_threadpool(thumbnail, path):
            raise HTTPException(status_code=400, detail='Invalid thumbnail arguments.')
    try:
        if await aioos.stat(path):
            return FileResponse(
                path=path,
                media_type=guess_type(filename or file_id)[0] or 'application/octet-stream',
            )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Not found')


def thumbnail(path: str):
    '''
    Specify the path and add a "@" followed by the arguments.

    This allows us to easily get the original file, make the changes,
    save the file with the full path, so the server never has to do
    the operation again, as long as the arguments are precisely the same.

    Arguments can be specified as followed:

        SXx         - Width, keeps aspect ratio
        SYx         - Height, keeps aspect ration. 
                      Ignored if SX is specified.
        ROTATEx     - Number of degrees you wise to 
                      rotate the image. Supports 
                      negative numbers.
        RESx        - Resolution, used for PDF 
                      files, the higher the number,
                      the better the quality.
        PAGEx       - Page index in the PDF document.

    The file format can be specified by ending the path with
    E.g. .jpg, .png, .tiff, etc.

    The arguments can be separated with _ or just
    don't separate them. Works either way. 

    Example:

        /foo/14bc...@SX1024_ROTATE90.png

    Resizes the image to a width of 1024, rotates it 90 degrees and converts 
    it to a PNG file.
    '''
    p = path.split('@')
    if len(p) != 2:
        return False
    if os.path.exists(path):
        return True
    if len(p[1]) > 40:
        raise HTTPException(status_code=400, detail='Parameters too long, max 40.')

    size_match, rotate_match, resolution_match, \
        page_match, format_match = __parse_arguments(p[1])

    # a specific page in a PDF document
    if page_match and page_match.group(1) != None:
        page = '[{}]'.format(page_match.group(1))
    else:
        # Prevent a dicom file or pdf file from extracting multiple images
        page = '[0]'

    o = {
        'filename': p[0]+page
    }
    if resolution_match and resolution_match.group(1) != None:
        o['resolution'] = int(resolution_match.group(1))

    try:
        with image.Image(**o) as img:
            if size_match:
                # resize, keep aspect ratio
                if size_match.group(1) != None:# width
                    img.transform(resize=size_match.group(1))
                elif size_match.group(2) != None:# height
                    img.transform(resize='x'+size_match.group(2))
            if rotate_match:
                if rotate_match.group(1) != None:
                    img.rotate(int(rotate_match.group(1)))
            if format_match:
                img.format = format_match.group(1)
            img.save(filename=path)
        return True
    except exceptions.BlobError:
        raise HTTPException(status_code=404, detail='Not found')

def __parse_arguments(arguments: str):
    size_match = re.search(
        r'SX([0-9]+)|SY([0-9]+)',
        arguments,
        re.I
    )
    rotate_match = re.search(
        r'ROTATE(-?[0-9]+)',
        arguments,
        re.I
    )
    resolution_match = re.search(
        r'RES([0-9]+)',
        arguments,
        re.I
    )
    page_match = re.search(
        r'PAGE([0-9]+)',
        arguments,
        re.I
    )
    format_match = re.search(
        r'\.([a-z0-9]{2,5})',
        arguments,
        re.I
    )
    return (
        size_match,
        rotate_match,
        resolution_match,
        page_match,
        format_match,
    )