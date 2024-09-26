from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_health():
    prev_store_path = config.store_path
    try:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
        assert response.text == 'OK'

        config.store_path = '/something/something'
        response = client.get('/health')
        assert response.status_code == 500
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'
    finally:
        config.store_path = prev_store_path
