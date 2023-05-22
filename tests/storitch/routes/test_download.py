import unittest, os
from unittest.mock import patch, Mock
from storitch.permanent_store import image_width_high
from storitch.routes.download import thumbnail

class Test(unittest.TestCase):

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
        self.assertEqual(info, (220, 163))


if __name__ == '__main__':
    unittest.main()