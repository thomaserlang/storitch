import tempfile
from io import StringIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_session() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = Path(temp_dir)
        config.api_keys = ['test']
        file = StringIO('this is a test file')
        start = True
        session = ''
        while True:
            d = file.read(1)
            response = client.request(
                method='POST' if start else 'PATCH',
                url='/store/session',
                content=d,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'X-Session': session,
                    'X-Filename': 'testæøå.txt'.encode('unicode-escape').decode(),
                    'X-Finished': 'false' if d else 'true',
                    'Authorization': 'test',
                },
            )
            start = False
            assert response.status_code < 400, response.text
            data = response.json()
            if 'session' in data:
                session = data['session']
            if not d:
                break
        assert (
            data['hash']
            == '5881707e54b0112f901bc83a1ffbacac8fab74ea46a6f706a3efc5f7d4c1c625'
        ), data['hash']
        assert data['type'] == 'file'
        assert data['filename'] == 'testæøå.txt', data['filename']

        response = client.get(f'/{data["file_id"]}')
        assert response.status_code == 200
        assert response.content == b'this is a test file'


@pytest.fixture
def upload_headers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    store = tmp_path / 'store'
    temp = tmp_path / 'temp'
    store.mkdir()
    temp.mkdir()
    monkeypatch.setattr(config, 'store_path', store)
    monkeypatch.setattr(config, 'temp_path', temp)
    monkeypatch.setattr(config, 'api_keys', ['test'])
    return {
        'Authorization': 'test',
        'Content-Type': 'application/octet-stream',
        'X-Filename': 'test.txt',
    }


@pytest.mark.parametrize(
    'chunks,checksum',
    [
        ([b'123456789'], '4waSgw=='),
        ([b'1234', b'56789', b''], '4waSgw=='),
        ([b''], 'AAAAAA=='),
    ],
)
def test_verified_session(
    upload_headers: dict[str, str], chunks: list[bytes], checksum: str
) -> None:
    for index, chunk in enumerate(chunks):
        final = index == len(chunks) - 1
        upload_headers['X-Finished'] = str(final).lower()
        if final:
            upload_headers['X-Checksum-CRC32C'] = checksum
        response = client.request(
            'POST' if index == 0 else 'PATCH',
            '/store/session',
            content=chunk,
            headers=upload_headers,
        )
        assert response.is_success, response.text
        if not final:
            upload_headers['X-Session'] = response.json()['session']
    result = response.json()
    assert result['checksum_crc32c'] == checksum
    assert client.get('/' + result['file_id']).content == b''.join(chunks)
    assert not list(config.temp_path.iterdir())


def test_mismatch_discards_session(upload_headers: dict[str, str]) -> None:
    start = client.post(
        '/store/session',
        content=b'1234',
        headers={**upload_headers, 'X-Finished': 'false'},
    )
    response = client.patch(
        '/store/session',
        content=b'corrupt',
        headers={
            **upload_headers,
            'X-Session': start.json()['session'],
            'X-Finished': 'true',
            'X-Checksum-CRC32C': '4waSgw==',
        },
    )
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'upload_checksum_mismatch'
    assert not list(config.temp_path.iterdir())
    assert not list(config.store_path.iterdir())


@pytest.mark.parametrize(
    'checksum,finished', [('invalid', True), ('YQ==', True), ('4waSgw==', False)]
)
def test_invalid_checksum_before_write(
    upload_headers: dict[str, str], checksum: str, finished: bool
) -> None:
    response = client.post(
        '/store/session',
        content=b'123456789',
        headers={
            **upload_headers,
            'X-Checksum-CRC32C': checksum,
            'X-Finished': str(finished).lower(),
        },
    )
    assert response.status_code == 422
    assert not list(config.temp_path.iterdir())


def test_verified_deduplication(
    upload_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, 'deduplication', True)
    headers = {**upload_headers, 'X-Checksum-CRC32C': '4waSgw=='}
    first = client.post('/store/session', content=b'123456789', headers=headers)
    second = client.post('/store/session', content=b'123456789', headers=headers)
    assert first.is_success and second.is_success
    assert first.json()['file_id'] == second.json()['file_id']
    assert second.json()['checksum_crc32c'] == '4waSgw=='
    assert not list(config.temp_path.iterdir())
