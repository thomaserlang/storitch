import unittest
import storitch
import io
import json
import tempfile
from datetime import datetime

class Store(object):

    @classmethod
    def store(cls, path, stream, hash_):
        return True

class test_main(unittest.TestCase):

    def setUp(self):
        storitch.app.debug = True
        storitch.app.config['STORE_ENGINE'] = Store
        self.app = storitch.app.test_client()

    def tearDown(self):
        pass

class test_app(test_main):

    def test_app(self):
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
        }])

if __name__ == '__main__':
    unittest.main()