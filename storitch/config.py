import logging
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from . import logger


class ConfigLoggingModel(BaseModel):
    level: Literal['notset', 'debug', 'info', 'warning', 'error', 'critical'] = 'info'
    path: str | None = None
    max_size: int = 100 * 1000 * 1000  # ~ 95 mb
    num_backups: int = 10


def get_config_path() -> Path | None:
    path: Path | None = None
    if os.environ.get('STORITCH__CONFIG', None):
        path = Path(os.environ['STORITCH__CONFIG'])
    if os.environ.get('STORITCH_CONFIG', None):
        path = Path(os.environ['STORITCH_CONFIG'])
    if path:
        if not os.path.isfile(path):
            raise Exception(f'Config: "{path}" could not be found.')
        logging.info(f'Using config: {path}')
        return Path(path)
    return None


class ConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='storitch__',
        env_nested_delimiter='__',
        validate_assignment=True,
        case_sensitive=False,
        yaml_file=get_config_path(),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )

    debug: bool = False
    port: int = 3000
    store_path: Path = Path('/var/storitch')
    api_keys: list[str] = []
    logging: ConfigLoggingModel = ConfigLoggingModel()
    image_extensions: list[str] = [
        'jpg',
        'jpeg',
        'jp2',
        'png',
        'tiff',
        'tif',
        'gif',
        'bmp',
        'bmp2',
        'bmp3',
        'dcm',
        'dicom',
        'webp',
        'heic',
        'heif',
        'avif',
        'jfif',
        'raw',
    ]
    allowed_resizes: list[int] = []
    allow_imagemagick_fallback: bool = True
    dir_mode: str = '755'
    file_mode: str = '444'
    temp_path: Path = Path(tempfile.gettempdir()) / 'storitch'
    content_disposition_type: str = 'inline'
    extract_metadata: bool = True
    sentry_dsn: str | None = None
    deduplication: bool = True


config = ConfigSettings()

os.makedirs(config.temp_path, exist_ok=True)
tempfile.tempdir = str(config.temp_path)
# Test that we can write to the temp dir
t = tempfile.TemporaryDirectory()
t.cleanup()

logger.set_logger(
    filename=f'storitch-{config.port}.log',
    path=config.logging.path or '',
    max_size=config.logging.max_size,
    num_backups=config.logging.num_backups,
    level=config.logging.level,
)
