import imghdr
import re
from wand import image

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
            SY7x        - Height, keeps aspect ration. 
                          Ignored if SX is specified.
            ROTATEx     - Number of degrees you wise to 
                          rotate the image. Supports 
                          negative numbers.
            RESx        - Resolution, used for PDF 
                          files, the higher the number,
                          the better the quality.
            PAGEx       - Page index in the PDF document.

        The file format can be specified by ending the path with
        E.g. .jpg, .png, .tiff, etc.

        The arguments can be separated with _ or just
        don't separate them. Works either way. 

        Example:

            /foo/14bc...@SX1024_ROTATE90.png

        Resizes the image to a width of 1024,
        rotates it 90 degrees and converts it
        to a png file.

        '''
        p = path.split('@')
        if len(p) != 2:
            return False
        size_match, rotate_match, resolution_match, page_match = cls.__parse_arguments(p[1])
        o = {
            'filename': p[0]
        }
        if resolution_match:
            # resolution
            if resolution_match.group(1) != None:
                o['resolution'] = int(resolution_match.group(1))
        if page_match:
            # a specific page in a PDF document
            if page_match.group(1) != None:
                path += '[{}]'.format(page_match.group(1))
        with image.Image(**o) as img:
            if size_match:
                # resize, keep aspect ratio
                if size_match.group(1) != None:# width
                    img.transform(resize=size_match.group(1))
                elif size_match.group(2) != None:# height
                    img.transform(resize='x'+size_match.group(2))
            if rotate_match:
                if rotate_match.group(1) != None:
                    img.rotate(int(rotate_match.group(1)))
            img.save(filename=path)
        return True

    @classmethod
    def __parse_arguments(cls, arguments):
        '''

        :param arguments: str
        :returns: tuple
            (
                size_match,
                rotate_match,
                resolution_match,
                page_match,
            )
        '''
        size_match = re.search(
            'SX(\d+)|SY(\d+)',
            arguments,
            re.I
        )
        rotate_match = re.search(
            'ROTATE(-?\d+)',
            arguments,
            re.I
        )
        resolution_match = re.search(
            'RES(\d+)',
            arguments,
            re.I
        )
        page_match = re.search(
            'PAGE(\d+)',
            arguments,
            re.I
        )
        return (
            size_match,
            rotate_match,
            resolution_match,
            page_match,
        )