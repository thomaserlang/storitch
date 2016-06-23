#coding=utf-8 
import re
import os
from wand import image
from wand import exceptions

class Image(object):

    @classmethod
    def thumbnail(cls, path):
        '''

        Specify the path and add a "@" followed by the arguments.

        This allows us to easily get the original file, make the changes,
        save the file with the full path, so the server never has to do
        the operation again, as long as the arguments are precisely the same.

        Arguments can be specified as followed:

            SXx         - Width, keeps aspect ratio
            SYx         - Height, keeps aspect ration. 
                          Ignored if SX is specified.
            S[X]x[Y]    - Specific size.
            ROTATEx     - Number of degrees you want to 
                          rotate the image. Supports 
                          negative numbers.

        The file format can be specified by ending the path with
        E.g. .jpg, .png, .tiff, etc.

        The arguments can be separated with _ or just
        don't separate them. Works either way. 

        Example:

            /foo/14bc...@SX1024_ROTATE90.png

        Resizes the image to a width of 1024, rotates it 90 degrees and converts 
        it to a PNG file.

        :param path: str
        '''
        p = path.split('@')
        if len(p) != 2:
            return False
        if os.path.exists(path):
            return True
        aspect_size_match, rotate_match, size_match, format_match = cls.__parse_arguments(p[1])
        o = {
            'filename': p[0]
        }
        with image.Image(**o) as img:
            if aspect_size_match:
                # resize, keep aspect ratio
                if aspect_size_match.group(1) != None:# width
                    img.transform(resize=aspect_size_match.group(1))
                elif size_match.group(2) != None:# height
                    img.transform(resize='x'+size_match.group(2))
            if size_match:
                img.resize(
                    width=int(crop_match.group(1)),
                    height=int(crop_match.group(2)),
                )
            if rotate_match:
                if rotate_match.group(1) != None:
                    img.rotate(int(rotate_match.group(1)))
            if format_match:
                img.format = format_match.group(1)
            img.save(filename=path)
        return True

    @classmethod
    def __parse_arguments(cls, arguments):
        '''

        :param arguments: str
        :returns: tuple
            (
                aspect_size_match,
                rotate_match,
                size_match,
                format_match
            )
        '''
        aspect_size_match = re.search(
            'SX(\d+)|SY(\d+)',
            arguments,
            re.I
        )
        rotate_match = re.search(
            'ROTATE(-?\d+)',
            arguments,
            re.I
        )        
        size_match = re.search(
            'S(\d+)X(\d+)',
            arguments,
            re.I
        )
        format_match = re.search(
            '\.([a-z]{2,5})',
            arguments,
            re.I
        )
        return (
            aspect_size_match,
            rotate_match,
            size_match,
            format_match,
        )

    @classmethod
    def info(cls, file_):
        file_.seek(0)
        try:
            with image.Image(file=file_) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                }
        except (ValueError, exceptions.MissingDelegateError):
            return None