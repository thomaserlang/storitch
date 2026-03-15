import logging
from io import BytesIO
from pathlib import Path
from typing import Annotated

import highdicom as hd
from fastapi import APIRouter, HTTPException, Response
from fastapi import Path as PathParam
from pydicom.errors import InvalidDicomError

from storitch.store_file import get_file_path

router = APIRouter(tags=['DICOM'])


@router.get(
    '/{file_id}/dicom/frames/{frames}',
    responses={200: {'content': {'multipart/related': {}}}},
)
async def get_dicom_frames_route(
    file_id: str,
    frames: Annotated[
        str,
        PathParam(
            description='Comma separated list of frame numbers. 1 based index.',
            examples=['1', '1,2'],
        ),
    ],
) -> Response:
    frame_numbers = [int(f) for f in frames.split(',')]
    try:
        return get_frames(get_file_path(file_id), frame_numbers)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail='Not found') from e
    except OSError as e:
        raise HTTPException(status_code=500, detail='Failed to open file') from e
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, does not look like an image'
        ) from e
    except InvalidDicomError as e:
        raise HTTPException(
            status_code=400, detail='Invalid DICOM file, could not read file'
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail='Internal server error') from e


_TS_TO_CT = {
    '1.2.840.10008.1.2.4.50': 'image/jpeg',  # JPEG Baseline
    '1.2.840.10008.1.2.4.51': 'image/jpeg',  # JPEG Extended
    '1.2.840.10008.1.2.4.57': 'image/jpeg',  # JPEG Lossless NH
    '1.2.840.10008.1.2.4.70': 'image/jpeg',  # JPEG Lossless
    '1.2.840.10008.1.2.4.80': 'image/jpeg',  # JPEG-LS Lossless
    '1.2.840.10008.1.2.4.81': 'image/jpeg',  # JPEG-LS Near-lossless
    '1.2.840.10008.1.2.4.90': 'image/jp2',  # JPEG 2000 Lossless
    '1.2.840.10008.1.2.4.91': 'image/jp2',  # JPEG 2000
    '1.2.840.10008.1.2.4.201': 'image/jphc',  # HTJ2K Lossless
    '1.2.840.10008.1.2.4.202': 'image/jphc',  # HTJ2K
    '1.2.840.10008.1.2.5': 'application/octet-stream',  # RLE Lossless
}


def get_frames(path: Path, frame_numbers: list[int]) -> Response:
    im = hd.imread(path, lazy_frame_retrieval=True)
    ts = (
        str(im.file_meta.TransferSyntaxUID)
        if hasattr(im, 'file_meta')
        else '1.2.840.10008.1.2.1'
    )
    frame_ct = _TS_TO_CT.get(ts, 'application/octet-stream')

    frames_bytes = []
    for fn in frame_numbers:
        frames_bytes.append(im.get_raw_frame(fn))

    parts = [(fb, frame_ct, ts) for fb in frames_bytes]
    multipart_ct = f'multipart/related; type="{frame_ct}"; boundary={_BOUNDARY}'
    return Response(content=_multipart(parts), media_type=multipart_ct)


def _multipart(parts: list[tuple[bytes, str, str]]) -> bytes:
    buf = BytesIO()
    for data, ct, ts in parts:
        buf.write(f'--{_BOUNDARY}\r\n'.encode())
        # transfer-syntax must be a Content-Type parameter, not a separate header
        buf.write(f'Content-Type: {ct}; transfer-syntax={ts}\r\n\r\n'.encode())
        buf.write(data)
        buf.write(b'\r\n')
    buf.write(f'--{_BOUNDARY}--\r\n'.encode())
    return buf.getvalue()


_BOUNDARY = 'DICOMwebBoundary'
