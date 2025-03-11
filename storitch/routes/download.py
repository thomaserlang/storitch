import asyncio
import logging
import os
import re
import time
from mimetypes import guess_type
from pathlib import Path
from typing import Annotated

from aiofile import async_open
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import StringConstraints

from storitch import config, store_file

router = APIRouter(tags=['Download'])


description = """
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
"""


@router.get('/{file_id}', response_class=FileResponse, description=description)
@router.get(
    '/{file_id}/{filename}',
    response_class=FileResponse,
    description=description,
    name='Download with filename',
)
@router.head('/{file_id}', description=description)
@router.head('/{file_id}/{filename}', description=description)
async def download(
    file_id: Annotated[
        str, StringConstraints(pattern=r'[a-zA-Z0-9-]+(@[a-zA-Z0-9_\-.]+)?')
    ],
    request: Request,
    filename: str | None = None,
):
    path = store_file.get_file_path(file_id)
    if '@' in file_id:
        converted = await convert(path)
        if not converted:
            raise HTTPException(status_code=500, detail='Failed to convert file.')
        path = converted

    try:
        stat_result = path.stat()
        media_type = guess_type(filename or file_id)[0] or 'application/octet-stream'

        if request.method == 'HEAD':
            return FileResponse(
                path,
                status_code=200,
                media_type=media_type,
                filename=filename,
                method='HEAD',
                stat_result=stat_result,
            )

        return range_requests_response(
            request=request,
            path=path,
            filename=filename or file_id,
            media_type=media_type,
            stat_result=stat_result,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Not found')
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail='Internal server error')


async def convert(path: Path):
    """
    Specify the path and add a "@" followed by the arguments.

    This allows us to easily get the original file, make the changes,
    save the file with the full path, so the server never has to do
    the operation again, as long as the arguments are precisely the same.
    """
    p = str(path).split('@')
    if len(p) != 2:
        raise HTTPException(status_code=400, detail='Invalid thumbnail arguments.')

    if len(p[1]) > 40:
        raise HTTPException(status_code=400, detail='Parameters too long, max 40.')

    if ext := path.suffix[1:]:
        if ext not in config.image_extensions:
            raise HTTPException(status_code=400, detail='Invalid file extension.')

    args = [
        '-quiet',
        '-auto-orient',
    ]
    size = _get_size(p[1], args)
    save_path = Path(f'{p[0]}@{size}{"." if ext else ""}{ext}')

    if save_path.exists():
        return save_path

    start_time = time.time()

    # "[0]" is to limit to the first image if e.g.
    # the file is a dicom and contains multiple images
    p = await asyncio.subprocess.create_subprocess_exec(
        'magick',
        f'{p[0]}[0]',
        *args,
        str(save_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, error = await p.communicate()

    execution_time = time.time() - start_time

    if error:
        logging.error(f'{path}: {error.decode()}')
        return
    else:
        logging.info(f'{path}: converted ({execution_time:.3f}s)')

    save_path.chmod(int(config.file_mode, 8))
    return save_path


def _get_size(arguments: str, convert_args: list[str]):
    size_match = re.search(r'SX([0-9]+)|SY([0-9]+)', arguments, re.I)
    if size_match:
        convert_args.append('-thumbnail')
        if size_match.group(1):
            is_allowed_resize_size(int(size_match.group(1)))
            convert_args.append(f'{size_match.group(1)}x')
            return f'SX{size_match.group(1)}'
        elif size_match.group(2):
            is_allowed_resize_size(int(size_match.group(2)))
            convert_args.append(f'x{size_match.group(2)}')
            return f'SY{size_match.group(2)}'
    return ''


def range_requests_response(
    request: Request,
    path: Path,
    filename: str,
    media_type: str,
    stat_result: os.stat_result,
):
    """Returns StreamingResponse using Range Requests of a given file"""

    file_size = stat_result.st_size
    range_header = request.headers.get('range')

    f = FileResponse(
        path=path,
        stat_result=stat_result,
        filename=filename,
        media_type=media_type,
        content_disposition_type=config.content_disposition_type,
    )
    headers = f.headers
    headers['accept-ranges'] = 'bytes'
    headers['content-encoding'] = 'identity'
    headers['access-control-expose-headers'] = (
        'content-type, accept-ranges, content-length, '
        'content-range, content-encoding'
    )
    start = 0
    end = file_size - 1
    status_code = status.HTTP_200_OK

    if range_header is not None and range_header != '':
        start, end = _get_range_header(range_header, file_size)
        size = end - start + 1
        headers['content-length'] = str(size)
        headers['content-range'] = f'bytes {start}-{end}/{file_size}'
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        _send_bytes(path, start, end),
        headers=headers,
        status_code=status_code,
    )


def _get_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    def _invalid_range():
        return HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f'Invalid request range (Range:{range_header!r})',
        )

    try:
        h = range_header.replace('bytes=', '').split('-')
        start = int(h[0]) if h[0] != '' else 0
        end = int(h[1]) if h[1] != '' else file_size - 1
    except ValueError:
        raise _invalid_range()

    if start > end or start < 0 or end > file_size - 1:
        raise _invalid_range()
    return start, end


async def _send_bytes(path: Path, start: int, end: int):
    async with async_open(path, mode='rb') as f:
        f.seek(start)
        while (pos := f.tell()) <= end:
            read_size = min(FileResponse.chunk_size, end + 1 - pos)
            yield await f.read(read_size)


def is_allowed_resize_size(size: int):
    if config.allowed_resizes and size not in config.allowed_resizes:
        raise HTTPException(status_code=400, detail=f'Size {size} not allowed.')
    return True
