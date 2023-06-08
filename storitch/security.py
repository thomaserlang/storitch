from typing import Annotated
from fastapi.security.api_key import APIKeyHeader
from fastapi import Header, Security, HTTPException
from . import config


async def validate_api_key(authorization: Annotated[str, Header(description='API Key')]):
    if authorization in config.api_keys:
        return authorization
    raise HTTPException(status_code=403, detail="Invalid API Key")