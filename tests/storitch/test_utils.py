import unittest
from storitch.utils import path_from_hash

class Test(unittest.TestCase):

    def test_path_from_hash(self):
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

if __name__ == '__main__':
    unittest.main()