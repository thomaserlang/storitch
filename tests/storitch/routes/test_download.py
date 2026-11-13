from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app
from storitch.store_file import get_file_path


@pytest.mark.parametrize(
    ('range_header', 'status', 'content', 'content_range'),
    [
        ('bytes=-3', 206, b'789', 'bytes 7-9/10'),
        ('bytes=7-99', 206, b'789', 'bytes 7-9/10'),
        ('bytes=10-', 416, b'', 'bytes */10'),
    ],
)
def test_download_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    range_header: str,
    status: int,
    content: bytes,
    content_range: str,
) -> None:
    monkeypatch.setattr(config, 'store_path', tmp_path)
    path = get_file_path('test-file')
    path.parent.mkdir(parents=True)
    path.write_bytes(b'0123456789')

    response = TestClient(app).get('/test-file', headers={'Range': range_header})
    assert response.status_code == status
    assert response.content == content
    assert response.headers['content-range'] == content_range


def test_download_head_and_if_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, 'store_path', tmp_path)
    path = get_file_path('test-file')
    path.parent.mkdir(parents=True)
    path.write_bytes(b'0123456789')
    client = TestClient(app)

    head = client.head('/test-file/example.txt')
    assert head.status_code == 200
    assert head.content == b''
    assert head.headers['content-length'] == '10'
    assert 'example.txt' in head.headers['content-disposition']

    response = client.get(
        '/test-file/example.txt',
        headers={'Range': 'bytes=7-', 'If-Range': '"old-etag"'},
    )
    assert response.status_code == 200
    assert response.content == b'0123456789'
    assert response.headers['etag'] == head.headers['etag']
