import os, uuid
import hashlib
import aiofiles
from aiofiles import os as aioos
from starlette.concurrency import run_in_threadpool
from wand import image
from . import utils, schemas, config


async def move_to_permanent_store(
        file_: aiofiles.tempfile.SpooledTemporaryFile, 
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
            chunk = await file_.read(128*1024)
            if not chunk:
                break
            await f.write(chunk)
            digest.update(chunk)
    hash_ = digest.hexdigest()
    file_chmod(file_id)
    return await upload_result(file_id, hash_, filename)
    

async def upload_result(file_id: str, hash_: str, filename: str):
    type_ = 'file'
    width = None
    height = None
    path = get_file_path(file_id)
    # If it's an image, extract its width and hight
    d = os.path.splitext(filename)
    if len(d) == 2:
        ext = d[1]
        if ext.lower() in config.image_exts:
            width, height = await run_in_threadpool(image_width_high, path)
            if width or height:
                type_ = 'image'
    
    return schemas.Upload_result(
        file_id=file_id,
        file_size=(await aioos.stat(path)).st_size,
        filename=filename,
        hash=hash_,
        type=type_,
        width=width,
        height=height,
    )


async def create_store_folder(file_id):
    dir = get_store_folder(file_id)
    if not await aioos.path.exists(dir):
        await aioos.makedirs(dir, mode=int(config.dir_mode, 8))
    return dir


def file_chmod(file_id):
    path = get_file_path(file_id)
    os.chmod(path, int(config.file_mode, 8))


def get_store_folder(file_id):
    return os.path.join(
        config.store_path,
        utils.path_from_file_id(file_id),
    )


def get_file_path(file_id):
    return os.path.join(
        get_store_folder(file_id),
        file_id,
    )


def image_width_high(path):
    try:
        with image.Image(filename=path) as img:
            return (img.width, img.height)
    except Exception:
        return (None, None)