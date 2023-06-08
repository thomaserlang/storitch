from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
from . import config

api_key_header = APIKeyHeader(name="authorization", auto_error=False)

async def validate_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header in config.api_keys:
        return api_key_header
    raise HTTPException(status_code=403, detail="Invalid API Key")