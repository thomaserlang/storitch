from filetype import Type


class M3shapeDCM(Type):
    MIME = 'application/3shapedcm'
    EXTENSION = '3shapedcm'

    def __init__(self) -> None:
        super().__init__(mime=M3shapeDCM.MIME, extension=M3shapeDCM.EXTENSION)

    def match(self, buf: bytes) -> bool:
        return buf.startswith(b'<HPS version="')
