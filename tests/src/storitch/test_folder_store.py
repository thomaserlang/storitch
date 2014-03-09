import unittest
import builtins
from mock import patch, mock_open, Mock
from storitch.folder_store import path_from_hash, Folder_store

class test_path_from_hash(unittest.TestCase):

    def test(self):
        hash_ = '1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014'

        path = path_from_hash(
            hash_,
            levels=1,
            length=2,
        )
        self.assertEqual(
            '/1b',
            path,
        )

        path = path_from_hash(
            hash_,
            levels=2,
            length=2,
        )
        self.assertEqual(
            '/1b/4f',
            path,
        )

        path = path_from_hash(
            hash_,
            levels=3,
            length=3,
        )
        self.assertEqual(
            '/1b4/f0e/985',
            path,
        )

class test_folder_store(unittest.TestCase):

    @patch('os.makedirs', Mock(return_value=True))
    def test_store(self):
        uploaded_file = mock_open(read_data='test1')
        store_file = mock_open()
        with patch('{}.open'.format(__name__), uploaded_file, create=True):
            with open('foo', 'wb') as f:
                with patch('storitch.folder_store.open', store_file, create=True):
                    Folder_store.store(
                        path='',
                        stream=f,
                        hash_='1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014',
                    )
                    store_file().write.assert_called_once_with('test1')

if __name__ == '__main__':
    unittest.main()