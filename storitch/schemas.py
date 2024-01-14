from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, constr

class Dicom_element(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    vr: str
    Value: Optional[list[any]] = None

class Metadata(BaseModel):
    exif: dict | None = None
    dicom: dict[str, Dicom_element] | None = None


class Upload_result(BaseModel):
    file_size: int
    filename: str | None
    hash: str | None
    file_id: str
    type: Literal['file', 'image']
    width: int | None = None    
    height: int | None = None
    metadata: Metadata | None = None

class Session_upload_start(BaseModel):
    filename: str
    finished: bool

class Session_upload_append(BaseModel):
    session: constr(min_length=36, max_length=36, pattern='^[0-9a-fA-F-]+$')
    filename: str
    finished: bool

class Session_result(BaseModel):
    session: str