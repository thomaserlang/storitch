import imghdr
import re
from wand import image

class Image(object):

    @classmethod
    def thumbnail(cls, path):
        p = path.split('@')
        if len(p) != 2:
            return False
        match = re.match(
            'SX([0-9]+)|SY([0-9]+)',
            p[1],
            re.I
        )
        with image.Image(filename=p[0]) as img:
            if match:
                if match.group(1) != None:
                    img.transform(resize=match.group(1))
                elif match.group(2) != None:                
                    img.transform(resize='x'+match.group(2))
            img.save(filename=path)
        return True