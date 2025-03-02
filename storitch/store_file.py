import hashlib
import uuid

from aiofile import async_open
from fastapi import UploadFile

from storitch.identify_file import get_file_info

from . import config, schemas, utils


async def move_to_permanent_store(
    file_: UploadFile,
    filename: str,
):
    file_id = str(uuid.uuid4())
    path = (await create_store_folder(file_id)) / file_id
    if path.exists():
        raise Exception(f'File already exists: {path}')

    digest = hashlib.sha256()
    async with async_open(path, mode='wb') as f:
        while chunk := await file_.read(128 * 1024):
            await f.write(chunk)
            digest.update(chunk)
    hash_ = digest.hexdigest()
    path.chmod(int(config.file_mode, 8))
    return await upload_result(file_id, hash_, filename)


async def upload_result(file_id: str, hash_: str, filename: str):
    path = get_file_path(file_id)
    file_info = await get_file_info(path, filename)
    return schemas.UploadResult(
        file_id=file_id,
        file_size=path.stat().st_size,
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
    if not dir.exists():
        dir.mkdir(parents=True, mode=int(config.dir_mode, 8))
    return dir


def get_store_folder(file_id: str):
    return config.store_path / utils.path_from_file_id(file_id)


def get_file_path(file_id: str):
    return get_store_folder(file_id) / file_id
