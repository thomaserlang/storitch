from typing import Annotated
from fastapi.security.api_key import APIKeyHeader
from fastapi import Header, Security, HTTPException
from . import config

api_key_header = APIKeyHeader(name="Authorization", auto_error=False, description="API Key")

async def validate_api_key(authorization: Annotated[str, Header(description='API Key')]):
    if api_key_header in config.api_keys:
        return api_key_header
    raise HTTPException(status_code=403, detail="Invalid API Key")