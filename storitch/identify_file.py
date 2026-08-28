import asyncio
import logging
import os.path
from decimal import Decimal, InvalidOperation
from pathlib import Path

import filetype
import pydicom
from fastapi.concurrency import run_in_threadpool
from filetype.types import (
    APPLICATION,
    ARCHIVE,
    AUDIO,
    DOCUMENT,
    FONT,
    VIDEO,
    image,
)
from pydantic import TypeAdapter
from pydicom.dataset import Dataset
from pydicom.valuerep import format_number_as_ds

from storitch import config, schemas
from storitch.filetype_matchers import M3shapeDCM
from storitch.ignore_errors import ignore_error

IMAGE = (
    image.Dcm(),
    image.Dwg(),
    image.Xcf(),
    image.Jpeg(),
    image.Jpx(),
    image.Apng(),
    image.Png(),
    image.Gif(),
    image.Webp(),
    image.Tiff(),
    image.Cr2(),
    image.Bmp(),
    image.Jxr(),
    image.Psd(),
    image.Ico(),
    image.Heic(),
    image.Avif(),
)


async def get_file_info(file_path: Path, filename: str = '') -> schemas.FileInfo:
    def identify(file_path: Path, filename: str) -> schemas.FileInfo:
        TYPES = list(
            IMAGE
            + AUDIO
            + VIDEO
            + FONT
            + DOCUMENT
            + ARCHIVE
            + APPLICATION
            + (M3shapeDCM(),)
        )
        kind = filetype.match(file_path, TYPES)
        if not kind:
            return schemas.FileInfo(
                type='file',
                extension=get_file_ext(filename),
            )

        type_ = 'file'
        if kind in ARCHIVE:
            type_ = 'archive'
        elif kind in DOCUMENT:
            type_ = 'document'
        elif kind in VIDEO:
            type_ = 'video'
        elif kind in AUDIO:
            type_ = 'audio'
        elif kind in APPLICATION:
            type_ = 'application'
        elif kind in FONT:
            type_ = 'font'

        return schemas.FileInfo(
            type=type_,
            extension=str(kind.extension),
        )

    file_info = await run_in_threadpool(
        identify, file_path=file_path, filename=filename
    )
    if file_info.type == 'image' or (file_info.extension in config.image_extensions):
        await set_image_info(file_info, file_path)
    return file_info


def get_file_ext(filename: str) -> str:
    d = os.path.splitext(filename)
    if len(d) != 2:
        return ''
    return d[1].lower()[1:]


async def set_image_info(file_info: schemas.FileInfo, path: Path) -> None:
    width, height = await image_width_high(path)

    file_info.width = width
    file_info.height = height
    if width:
        file_info.type = 'image'

    if not config.extract_metadata:
        return
    try:
        if file_info.extension == 'dcm':
            elements = await run_in_threadpool(get_dicom_elements, path)
            if elements:
                file_info.metadata = schemas.Metadata(dicom=elements)
        else:
            exif = await run_in_threadpool(get_image_exif, path)
            if exif:
                file_info.metadata = schemas.Metadata(exif=exif)
    except Exception as e:
        logging.exception(e)


async def image_width_high(path: Path) -> tuple[int | None, int | None]:
    # "[0]" is to limit to the first image if e.g.
    #  the file is a dicom and contains multiple images
    p = await asyncio.subprocess.create_subprocess_exec(
        'identify',
        '-quiet',
        '-ping',
        '-format',
        '%w %h',
        f'{path}[0]',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    data, error = await p.communicate()
    if (error and not ignore_error(error.decode())) or not data:
        logging.error(data)
        logging.warning(error.decode())
        return (None, None)
    r = data.decode().split(' ')
    return (int(r[0]), int(r[1]))


def get_image_exif(path: Path) -> dict[str, str | int | list[str]] | None:
    from PIL import ExifTags, Image

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return {}
            d = {}
            for tag, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag)
                if not tag_name:
                    continue
                try:
                    if tag_name:
                        if isinstance(value, tuple):
                            value = [str(v) for v in value]
                        d[tag_name] = (
                            str(value)
                            if not isinstance(value, (str, int, list))
                            else value
                        )
                except Exception:
                    pass
            ta = TypeAdapter(dict[str, str | int | list[str]])
            return ta.validate_python(d)
    except Exception as e:
        logging.exception(e)
        return None


def get_dicom_elements(path: Path) -> dict[str, dict] | None:
    try:
        with pydicom.dcmread(path, stop_before_pixels=True) as dataset:
            _normalize_dicom_decimal_strings(dataset)
            return dataset.to_json_dict(suppress_invalid_tags=True)
    except Exception as e:
        logging.exception(e)
        return None


def _normalize_dicom_decimal_strings(dataset: Dataset) -> None:
    """Make overlong numeric DS values valid without discarding their sequences."""
    for element in dataset.iterall():
        if element.VR != 'DS' or element.value is None:
            continue

        values = list(element.value) if element.VM > 1 else [element.value]
        normalized_values = []
        changed = False
        for value in values:
            value_text = str(value)
            if len(value_text) <= 16:
                normalized_values.append(value)
                continue

            try:
                normalized_values.append(format_number_as_ds(Decimal(value_text)))
            except (InvalidOperation, TypeError, ValueError):
                normalized_values.append(value)
                continue
            changed = True

        if changed:
            element.value = (
                normalized_values if element.VM > 1 else normalized_values[0]
            )
