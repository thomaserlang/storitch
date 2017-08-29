#coding=utf-8 
import unittest
import os
from mock import patch, Mock
from storitch.image import Image


class test_image(unittest.TestCase):

    def test_thumbnail(self):
        m = Mock
        img = Mock()
        m.__enter__ = Mock(return_value=img)
        m.__exit__ = Mock(return_value=False)

        self.assertFalse(
            Image.thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014')
        )

        with patch('wand.image.Image', m, create=True):
            Image.thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014@SY123_ROTATE180.png')
            img.transform.assert_called_with(resize='x123')
            img.rotate.assert_called_with(180)

        with patch('wand.image.Image', m, create=True):
            Image.thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014@SX200_ROTATE-180RES200.png')
            img.transform.assert_called_with(resize='200')
            img.rotate.assert_called_with(-180)
            self.assertEqual(img.format, 'png')

    def test_info(self):
        with open(os.path.join(os.path.dirname(__file__), 'image1.png'), 'rb') as f:
            info = Image.info(f, f.name, ['.png'])
            self.assertEqual(info, {
                'width': 220,
                'height': 163,
            })

if __name__ == '__main__':
    unittest.main()