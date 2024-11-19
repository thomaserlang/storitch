import os
import tempfile

from fastapi.testclient import TestClient

from storitch import config
from storitch.main import app

client = TestClient(app)


def test_metadata():
    with tempfile.TemporaryDirectory() as temp_dir:
        config.store_path = temp_dir
        config.api_keys = ['test']
        file1 = os.path.realpath(__file__ + '/../../../Canon_40D.jpg')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(('file', ('Canon_40D.jpg', open(file1, 'rb'))),),
        )
        assert response.status_code == 201, response.text

        data = response.json()
        assert data[0]['metadata']['exif']['DateTime'] == '2008:07:31 10:38:11', data[
            0
        ]['metadata']['exif']
        assert data[0]['type'] == 'image'
        assert data[0]['extension'] == 'jpg'

        file2 = os.path.realpath(__file__ + '/../../../0002.DCM')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(('file', ('0002.DCM', open(file2, 'rb'))),),
        )
        assert response.status_code == 201, response.text

        data = response.json()
        assert data[0]['type'] == 'image'
        assert data[0]['extension'] == 'dcm'

        file3 = os.path.realpath(__file__ + '/../../../0003')
        response = client.post(
            '/store',
            headers={'Authorization': 'test'},
            files=(('file', ('0003', open(file3, 'rb'))),),
        )
        assert response.status_code == 201, response.text

        data = response.json()
        assert data[0]['type'] == 'image'
        assert data[0]['extension'] == 'dcm'
        assert data[0]['metadata']['dicom']['00080020']['Value'][0] == '19941013', data[
            0
        ]['metadata']['dicom']['00080020']
