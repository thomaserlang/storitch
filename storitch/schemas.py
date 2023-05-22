from typing import Literal
from pydantic import BaseModel

class Upload_result(BaseModel):
    file_size: int
    filename: str | None
    hash: str | None
    file_id: str
    type: Literal['file', 'image']
    width: int | None
    height: int | None


class Session_upload_start(BaseModel):
    filename: str
    finished: bool

class Session_upload_append(BaseModel):
    session: str
    filename: str
    finished: bool

class Session_result(BaseModel):
    session: str