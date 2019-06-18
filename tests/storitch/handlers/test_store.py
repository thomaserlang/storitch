import unittest, tempfile, shutil, os
from unittest.mock import patch, Mock
from storitch.handlers.store import move_to_permanent_store, thumbnail, image_width_high
from storitch import config

class Test(unittest.TestCase):

    def test_move_to_permanent_store(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'test')
            f.flush()
            tempname = f.name
        t = tempfile.TemporaryDirectory()
        config['store_path'] = t.name
        try:
            r = move_to_permanent_store(tempname, 'test')
            self.assertEqual(r['hash'], '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08')
            self.assertEqual(r['filesize'], 4)
            self.assertTrue(r['stored'])
            self.assertEqual(r['filename'], 'test')
        finally:
            t.cleanup()

    def test_thumbnail(self):
        m = Mock
        img = Mock()
        m.__enter__ = Mock(return_value=img)
        m.__exit__ = Mock(return_value=False)

        self.assertFalse(
            thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014')
        )

        with patch('wand.image.Image', m, create=True):
            thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014@SY123_ROTATE180.png')
            img.transform.assert_called_with(resize='x123')
            img.rotate.assert_called_with(180)

        with patch('wand.image.Image', m, create=True):
            thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014@SX200_ROTATE-180RES200.png')
            img.transform.assert_called_with(resize='200')
            img.rotate.assert_called_with(-180)
            self.assertEqual(img.format, 'png')

    def test_image_width_high(self):
        info = image_width_high(os.path.join(os.path.dirname(__file__), 'image1.png'))
        self.assertEqual(info, {
            'width': 220,
            'height': 163,
        })


if __name__ == '__main__':
    unittest.main()