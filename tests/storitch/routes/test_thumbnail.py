import io
import os
import tempfile

from fastapi.testclient import TestClient
from PIL import Image

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_thumbnail():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
        config.api_keys = ['test']
        file1 = os.path.realpath(__file__ + '/../../../test.png')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(
                ('file', ('test.png', open(file1, 'rb'))),
            ),
        )
        assert response.status_code == 201, response.text

        data = response.json()

        response = client.get(
            f'/{data[0]["file_id"]}@SX2.jpg',
        )
        assert response.status_code == 200, response.text

        with Image.open(io.BytesIO(response.content)) as image:
            assert image.format == 'JPEG', image.format

        response = client.get(
            f'/{data[0]["file_id"]}@SX2.webp',
        )
        assert response.status_code == 200, response.text

        with Image.open(io.BytesIO(response.content)) as image:
            assert image.format == 'WEBP', image.format
        
        response = client.get(
            f'/{data[0]["file_id"]}@.ps',
        )
        assert response.status_code == 400, response.text


def test_dcm_thumbnail():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
        config.api_keys = ['test']
        file1 = os.path.realpath(__file__ + '/../../../0002.DCM')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(
                ('file', ('0002.DCM', open(file1, 'rb'))),
            ),
        )
        assert response.status_code == 201, response.text

        data = response.json()

        response = client.get(
            f'/{data[0]["file_id"]}@.jpg',
        )
        assert response.status_code == 200, response.text

        with Image.open(io.BytesIO(response.content)) as image:
            assert image.format == 'JPEG', image.format