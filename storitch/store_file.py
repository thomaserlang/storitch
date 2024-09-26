import hashlib
import os
import uuid

import aiofiles
from aiofiles import os as aioos
from fastapi import UploadFile

from storitch.identify_file import get_file_info

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
    path = get_file_path(file_id)
    file_info = await get_file_info(path, filename)
    return schemas.UploadResult(
        file_id=file_id,
        file_size=(await aioos.stat(path)).st_size,
        filename=filename,
        hash=hash_,
        type=file_info.type,
        extension=file_info.extension,
        width=file_info.width,
        height=file_info.height,
        metadata=file_info.metadata,
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
