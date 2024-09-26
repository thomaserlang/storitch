import asyncio
import hashlib
import logging
import os
import uuid

import aiofiles
from aiofiles import os as aioos
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import TypeAdapter

from . import config, schemas, utils


async def move_to_permanent_store(
    file_: UploadFile,
    filename: str,
):
    file_id = str(uuid.uuid4())
    dir = await create_store_folder(file_id)
    path = os.path.join(dir, file_id)
    if await aioos.path.exists(path):
        raise Exception(f'File already exists: {path}')

    digest = hashlib.sha256()
    async with aiofiles.open(path, mode='wb') as f:
        while True:
            chunk = await file_.read(128 * 1024)
            if not chunk:
                break
            await f.write(chunk)
            digest.update(chunk)
    hash_ = digest.hexdigest()
    os.chmod(path, int(config.file_mode, 8))
    return await upload_result(file_id, hash_, filename)


async def upload_result(file_id: str, hash_: str, filename: str):
    data = {}
    path = get_file_path(file_id)
    ext = get_file_ext(filename)
    if is_image(ext):
        data = await get_image_data(path, ext)
    if not data:
        data = {'type': 'file'}
    return schemas.Upload_result(
        file_id=file_id,
        file_size=(await aioos.stat(path)).st_size,
        filename=filename,
        hash=hash_,
        **data,  # type: ignore
    )


async def create_store_folder(file_id: str):
    dir = get_store_folder(file_id)
    if not await aioos.path.exists(dir):
        await aioos.makedirs(dir, mode=int(config.dir_mode, 8))
    return dir


def get_store_folder(file_id: str):
    return os.path.join(
        config.store_path,
        utils.path_from_file_id(file_id),
    )


def get_file_path(file_id: str):
    return os.path.join(
        get_store_folder(file_id),
        file_id,
    )


def is_image(ext: str):
    return ext in config.image_exts


def get_file_ext(filename: str):
    d = os.path.splitext(filename)
    if len(d) != 2:
        return ''
    return d[1].lower()


async def get_image_data(path: str, ext: str):
    width, height = await image_width_high(path)
    if not width or not height:
        return {}
    data = {
        'type': 'image',
        'width': width,
        'height': height,
    }
    if not config.extract_metadata:
        return data

    if ext in ('.dcm', '.dicom'):
        elements = await run_in_threadpool(get_dicom_elements, path)
        if elements:
            data['metadata'] = schemas.Metadata(dicom=elements)
    else:
        exif = await run_in_threadpool(get_image_exif, path)
        if exif:
            data['metadata'] = schemas.Metadata(exif=exif)
    return data


async def image_width_high(path: str):
    # "[0]" is to limit to the first image if e.g. the file is a dicom and contains multiple images
    p = await asyncio.subprocess.create_subprocess_exec(
        'identify',
        '-ping',
        '-format',
        '%w %h',
        f'{path}[0]',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    data, error = await p.communicate()
    if error:
        logging.error(f'{path}: {str(error.decode())}')
        return (None, None)
    r = data.decode().split(' ')
    return (int(r[0]), int(r[1]))


def get_image_exif(path: str):
    from PIL import ExifTags, Image

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return {}
            d = {}
            for tag, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag)
                try:
                    if tag_name:
                        d[tag_name] = (
                            str(value)
                            if not isinstance(value, str)
                            and not isinstance(value, int)
                            and not isinstance(value, tuple)
                            else value
                        )
                except Exception:
                    pass
            return d
    except Exception:
        return None


def get_dicom_elements(path: str):
    import pydicom

    try:
        with pydicom.dcmread(path, stop_before_pixels=True) as dataset:
            ta = TypeAdapter(dict[str, schemas.Dicom_element])
            return ta.validate_python(dataset.to_json_dict())
    except Exception:
        return None
