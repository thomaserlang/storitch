from filetype import Type


class M3shapeDCM(Type):
    MIME = 'application/3shapedcm'
    EXTENSION = '3shapedcm'

    def __init__(self):
        super(M3shapeDCM, self).__init__(mime=M3shapeDCM.MIME, extension=M3shapeDCM.EXTENSION)

    def match(self, buf):
        return buf.startswith(b'<HPS version="')