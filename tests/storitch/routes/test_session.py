import tempfile
from io import StringIO

from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
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
