import os
import tempfile

from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_health():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
        response = client.get('/health')
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
        assert response.text == 'OK'
        os.rmdir(config.store_path)

        config.store_path = '/something/something'
        response = client.get('/health')
        assert response.status_code == 500
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
