import unittest
import os
from mock import patch, mock_open, Mock
from storitch.image import Image
from wand import image

class test_image(unittest.TestCase):

    def test_thumbnail(self):
        self.assertFalse(
            Image.thumbnail('1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014')
        )

        thumbnail = '1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014@SX80.png'
        self.assertTrue(
            Image.thumbnail(thumbnail)
        )
        try:
            with image.Image(filename=thumbnail) as im:
                w, h = im.size
                self.assertEqual(w, 80)                 
        finally:
            if os.path.exists(thumbnail):
                os.remove(thumbnail)
        try:
            thumbnail = '1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014@SY123.png'
            self.assertTrue(
                Image.thumbnail(thumbnail)
            )
            with image.Image(filename=thumbnail) as im:
                w, h = im.size
                self.assertEqual(h, 123)     
        finally:
            if os.path.exists(thumbnail):
                os.remove(thumbnail)

if __name__ == '__main__':
    unittest.main()