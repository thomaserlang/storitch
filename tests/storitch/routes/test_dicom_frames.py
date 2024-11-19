import os
import tempfile

from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_dicom_frames():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
        config.api_keys = ['test']

        file1 = os.path.realpath(__file__ + '/../../../0002.DCM')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(('file', ('0002.DCM', open(file1, 'rb'))),),
        )

        data = response.json()
        assert data[0]['type'] == 'image'
        assert data[0]['extension'] == 'dcm'

        response = client.get(
            f'/{data[0]["file_id"]}/dicom/frames/1',
        )
        assert response.status_code == 200, response.text
        assert response.headers['Content-Type'].startswith(
            'multipart/related; boundary='
        )

        response = client.get(
            f'/{data[0]["file_id"]}/dicom/frames/2',
        )
        assert response.status_code == 200, response.text
        assert response.headers['Content-Type'].startswith(
            'multipart/related; boundary='
        )

        response = client.get(
            f'/{data[0]["file_id"]}/dicom/frames/1,2',
        )
        assert response.status_code == 200
        # test that boundry is 3 times in the response
        assert response.text.count('Content-Type:') == 2
