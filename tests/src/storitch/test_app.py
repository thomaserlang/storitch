#coding=utf-8 
import unittest
import storitch
import io
import json
import tempfile
import time
from datetime import datetime
from unittest.mock import patch, Mock

class test_main(unittest.TestCase):

    def setUp(self):
        storitch.app.debug = True
        storitch.app.config['STORE_PATH'] = tempfile.gettempdir()
        self.app = storitch.app.test_client()

    def tearDown(self):
        pass

class test_app(test_main):

    def test_text_file(self):
        data = {}
        response = self.app.post(
            '/store', 
            data={
                'file': (
                    io.BytesIO(b'test1'), 
                    'test1.txt',
                )
            }
        )
        files = json.loads(response.data.decode('utf8'))
        self.assertEqual(files, [{
            'hash': '1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014',
            'stored': True,
            'type': 'unknown',
            'filename': 'test1.txt',
            'filesize': 5,
        }])

        # test get original file
        response = self.app.get(files[0]['hash'])
        self.assertEqual(response.data, b'test1')

        # test resize
        m = Mock
        img = Mock()
        m.__enter__ = Mock(return_value=img)
        m.__exit__ = Mock(return_value=False)
        with patch('wand.image.Image', m, create=True):
            with patch('storitch.send_file', Mock(return_value=b'test1')):
                self.app.get(files[0]['hash']+'@SX200.jpg')
                img.transform.assert_called_with(resize='200')
                self.assertEqual(response.data, b'test1')

if __name__ == '__main__':
    unittest.main()