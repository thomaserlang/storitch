import os
import tempfile

from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_multipart():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
        config.api_keys = ['test']
        file1 = os.path.realpath(__file__ + '/../../../test.png')
        file2 = os.path.realpath(__file__ + '/../../../Canon_40D.jpg')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(
                ('file', ('test.png', open(file1, 'rb'))),
                ('file', ('Canon_40D.jpg', open(file2, 'rb'))),
            ),
        )
        assert response.status_code == 201, response.text
        assert response.headers['content-type'] == 'application/json'
        data = response.json()
        assert (
            data[0]['hash']
            == '1171aad9f52efe4f577ccabec4aaeb063e28a80978f3853721381bca2b5fe501'
        )
        assert data[0]['filename'] == 'test.png'
        assert data[0]['file_size'] == 120
        assert data[0]['type'] == 'image'
        assert data[0]['width'] == 5
        assert data[0]['height'] == 5
        assert (
            data[1]['hash']
            == '6bfdabd4fc33d112283c147acccc574e770bbe6fbdbc3d4da968ba7b606ecc2f'
        )
        assert data[1]['filename'] == 'Canon_40D.jpg'
        assert data[1]['file_size'] == 7958
        assert data[1]['type'] == 'image'
        assert data[1]['width'] == 100
        assert data[1]['height'] == 68
