#coding=utf-8 
import unittest
import io
import os
from unittest.mock import patch, mock_open, Mock
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
            '1b',
            path,
        )

        path = path_from_hash(
            hash_,
            levels=2,
            length=2,
        )
        self.assertEqual(
            '1b/4f',
            path,
        )

        path = path_from_hash(
            hash_,
            levels=3,
            length=3,
        )
        self.assertEqual(
            '1b4/f0e/985',
            path,
        )

class test_folder_store(unittest.TestCase):

    @patch('os.makedirs', Mock(return_value=True))
    @patch('os.chmod', Mock(return_value=True))
    def test_store(self):
        # test store
        m = Mock()
        m.filename = 'test'
        m.stream = io.BytesIO(b'test1')
        m.save = Mock()
        Folder_store.store(
            path='/test_folder',
            file=m,
            hash_='1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014',
        )
        m.save.assert_called_once_with(
            os.path.normpath('/test_folder/1b/4f/1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014'), 
        )

    def test_get(self):
        # test get
        self.assertEqual(
            Folder_store.get(
                path='/test_folder',
                hash_='1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014',
            ),
            os.path.normpath('/test_folder/1b/4f/1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014'),
        )

if __name__ == '__main__':
    unittest.main()