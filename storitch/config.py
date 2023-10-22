import logging
import os, yaml, tempfile
import pathlib
from typing import Literal
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings
from . import logger

class ConfigLoggingModel(BaseModel):
    level: Literal['notset', 'debug', 'info', 'warn', 'error', 'critical'] = 'warn'
    path: pathlib.Path | None = None
    max_size: int = 100 * 1000 * 1000 # ~ 95 mb
    num_backups: int = 10

class ConfigModel(BaseSettings):
    debug: bool = False
    port: int = 3000
    store_path: str = '/var/storitch'
    api_keys: list[str] = []
    logging: ConfigLoggingModel = ConfigLoggingModel()
    image_exts: list[str] = [
        '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.gif',
        '.bmp', '.bmp2', '.bmp3', '.dcm', '.dicom', '.webp',
        '.heic', '.heif', '.avif'
    ]
    allowed_resizes: list[int] = []
    dir_mode: str = '755'
    file_mode: str = '444'
    temp_path: str = '/var/storitch/tmp'

    model_config = ConfigDict(
        env_prefix='storitch_',
        env_nested_delimiter='.',
        validate_assignment=True,
        case_sensitive=False,
    )

config: ConfigModel

default_paths = [
    '~/storitch.yaml',
    './storitch.yaml',
    '../storitch.yaml',
    '/etc/storitch/storitch.yaml',
    '/etc/storitch.yaml',
    '~/storitch.yml',
    './storitch.yml',
    '../storitch.yml',
    '/etc/storitch/storitch.yml',
    '/etc/storitch.yml',
]
path = os.environ.get('STORITCH_CONFIG', None)
if not path:
    for p in default_paths:
        p = os.path.expanduser(p)
        if os.path.isfile(p):
            path = p
            break
if path:
    if not os.path.isfile(path):
        raise Exception(f'Config: "{path}" could not be found.')
    logging.info(f'Using config: {path}')
    with open(path, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        config = ConfigModel(**data)
else:
    config = ConfigModel()

os.makedirs(config.temp_path, exist_ok=True)
tempfile.tempdir = config.temp_path
# Test that we can write to the temp dir
t = tempfile.TemporaryDirectory()
t.cleanup()

logger.set_logger(
    filename=f'storitch-{config.port}.log',
    path=config.logging.path,
    max_size=config.logging.max_size,
    num_backups=config.logging.num_backups,
    level=config.logging.level,
)