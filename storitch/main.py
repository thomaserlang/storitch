import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from storitch import config

from .routes import (
    dicom_frames_routes,
    download_convert_routes,
    file_info_routes,
    health_routes,
    multipart_routes,
    session_routes,
)

sentry_sdk.init(dsn=config.sentry_dsn)

app = FastAPI(
    title='Storitch',
    description='A simple file storage service and thumbnail generator.',
    version='2.1',
)

app.include_router(multipart_routes.router)
app.include_router(session_routes.router)
app.include_router(health_routes.router)
app.include_router(download_convert_routes.router)
app.include_router(dicom_frames_routes.router)
app.include_router(file_info_routes.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({'detail': exc.errors(), 'body': exc.body}),
    )


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            'code': 0,
            'message': 'Internal server error',
        },
        headers={
            'access-control-allow-origin': '*',
        },
    )
