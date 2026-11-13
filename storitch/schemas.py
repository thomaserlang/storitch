from typing import Annotated, Literal

from pydantic import Base64Bytes, BaseModel, Field, StringConstraints

CRC32C = Annotated[
    Base64Bytes,
    Field(
        min_length=4,
        max_length=4,
        # Validation uses decoded bytes; OpenAPI describes the Base64 header.
        json_schema_extra={'minLength': 8, 'maxLength': 8},
    ),
]


class Metadata(BaseModel):
    exif: dict[str, str | int | list[str]] | None = None
    dicom: dict[str, dict] | None = None


FileTypes = Literal[
    'file', 'image', 'video', 'audio', 'archive', 'document', 'font', 'application'
]


class UploadResult(BaseModel):
    checksum_crc32c: str | None = None
    file_size: int
    filename: str | None
    hash: str | None
    file_id: str
    type: FileTypes
    extension: str | None = None
    width: int | None = None
    height: int | None = None
    metadata: Metadata | None = None


class FileInfo(BaseModel):
    extension: str | None
    type: FileTypes
    width: int | None = None
    height: int | None = None
    metadata: Metadata | None = None


class SessionUploadStart(BaseModel):
    filename: str
    finished: bool


class SessionUploadAppend(BaseModel):
    session: Annotated[
        str, StringConstraints(min_length=36, max_length=36, pattern='^[0-9a-fA-F-]+$')
    ]
    filename: str
    finished: bool


class SessionResult(BaseModel):
    session: str
