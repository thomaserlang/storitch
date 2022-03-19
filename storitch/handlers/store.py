import asyncio
from typing import Union, Dict, List, Any, Tuple, Optional
import json, os, re, shutil, mimetypes, good
import uuid
import aiofiles
from tornado import web
from storitch import utils, config
from storitch.decorators import run_on_executor
from wand import image, exceptions

class Base_handler(web.RequestHandler):

    def write_object(self, data: Union[Dict, List]) -> None:
        self.set_json_headers()
        self.write(json.dumps(data))

    def set_json_headers(self) -> None:
        self.set_header('Cache-Control', 'no-cache, must-revalidate')
        self.set_header('Expires', 'Sat, 26 Jul 1997 05:00:00 GMT')
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code: int, **kwargs) -> None:
        self.set_json_headers()
        error = {'error': 'Unknown error'}
        if 'exc_info' in kwargs:
            error['error'] = str(kwargs['exc_info'][1])
        self.set_status(status_code)
        self.write_object(error)

    @run_on_executor
    def copy_to_permanent_store(self, temp_path: str, filename: str) -> Dict[str, Any]:
        try:
            return copy_to_permanent_store(temp_path, filename)
        finally:
            os.remove(temp_path)

    @property
    def executor(self):
        return self.application.settings['executor']

    def get_content_type(self, path: str) -> str:
        # From: https://www.tornadoweb.org/en/stable/_modules/tornado/web.html#StaticFileHandler
        mime_type, encoding = mimetypes.guess_type(path)
        # per RFC 6713, use the appropriate type for a gzip compressed file
        if encoding == "gzip":
            return "application/gzip"
        # As of 2015-07-21 there is no bzip2 encoding defined at
        # http://www.iana.org/assignments/media-types/media-types.xhtml
        # So for that (and any other encoding), use octet-stream.
        elif encoding is not None:
            return "application/octet-stream"
        elif mime_type is not None:
            return mime_type
        # if mime_type not detected, use application/octet-stream
        else:
            return "application/octet-stream"

class Multipart_handler(Base_handler):

    async def post(self) -> None:
        if 'multipart/form-data' not in self.request.headers.get('Content-Type').lower():
            raise web.HTTPError(400, 
                'Content-Type must be multipart/form-data, was: {}'.format(
                    self.request.headers.get('Content-Type')
                )
            )

        if not self.request.files:
            raise web.HTTPError(400, 'No files uploaded')

        self.set_status(201)
        wait_for = []
        for n in self.request.files:
            for f in self.request.files[n]:
                wait_for.append(
                    self.save(f['filename'], f['body'])
                )
                f['body'] = None
        results = await asyncio.gather(*wait_for)
        self.write_object(results)

    async def save(self, filename: str, body: bytes):
        temp_path = os.path.join(
            config['temp_path'],
            str(uuid.uuid4()),
        )
        async with aiofiles.open(temp_path, 'wb', executor=self.executor) as f:
            await f.write(body)
        return await self.copy_to_permanent_store(temp_path, filename)

@web.stream_request_body
class Session_handler(Base_handler):

    __schema__ = good.Schema({
        'finished': good.Boolean(),
        'filename': good.All(str, good.Length(min=1, max=255)),
        good.Optional('session'): str,
    })

    def prepare(self) -> None:
        if 'application/octet-stream' not in self.request.headers.get('Content-Type').lower():
            raise web.HTTPError(400, 
                'Content-Type must be application/octet-stream, was: {}'.format(
                    self.request.headers.get('Content-Type')
                )
            )

        j = self.request.headers.get('storitch-json', None)
        if not j:
            raise web.HTTPError(400, 'Header: storitch-json must be set')

        data = json.loads(j)        

        self.h_finished = data['finished']
        self.h_filename = data['filename']
        self.h_session = data.get('session')

        if not self.h_session:
            self.h_session = str(uuid.uuid4())

        self.temp_path = os.path.join(
            config['temp_path'], 
            self.h_session
        )
    
    async def data_received(self, chunk: bytes) -> None:
        async with aiofiles.open(self.temp_path, 'ab', executor=self.executor) as f:
            await f.write(chunk)

    async def put(self) -> None:
        if self.h_finished:
            r = await self.copy_to_permanent_store(self.temp_path, self.h_filename)
            self.write_object(r)
        else:
            self.write_object({
                'session': self.h_session,
            })

    def validate_json(self, data: Dict[str, Any]) -> Union[Dict[str, Any], List]:
        try:
            return self.__schema__(data)  
        except good.MultipleInvalid as ee:
            data = []
            for e in ee:
                data.append(
                    '{}: {}'.format(
                        '.'.join(str(x) for x in e.path),
                        e.message,
                    )
                )
            raise web.HTTPError(400,' - '.join(d for d in data))
        except good.Invalid as e:
            raise web.HTTPError(400, '{}: {}'.format(
                '.'.join(str(x) for x in e.path),
                e.message,
            ))

class Download_handler(Base_handler):

    async def get(self, hash_: Optional[str] = None) -> None:
        if not hash_ or len(hash_) < 64:
            raise web.HTTPError(400, 'Please specify a file hash')
        path = os.path.join(
            config['store_path'],
            utils.path_from_hash(hash_),
            hash_
        )
        if not os.path.exists(path.split('@')[0]):
            raise web.HTTPError(404)
            
        if '@' in hash_:
            path = await self.thumbnail(path)
            if not path:
                self.write('Failed to create the thumbnail')
        self.set_header('Content-Type', self.get_content_type(path))
        async with aiofiles.open(path, 'rb') as f:
            self.set_header('Content-Length', os.fstat(f.fileno()).st_size)
            while True:
                d = await f.read(16384)
                if not d:
                    break
                self.write(d)
                self.flush()

    @run_on_executor
    def thumbnail(self, path: str) -> str:
        if thumbnail(path):
            return path

def copy_to_permanent_store(temp_path: str, filename: str) -> Dict[str, Any]:
    hash_ = utils.file_sha256(temp_path)
    
    dir = os.path.join(
        config['store_path'],
        utils.path_from_hash(hash_),
    )
    if not os.path.exists(dir):
        os.makedirs(dir, mode=int(config['dir_mode'], 8))
    path = os.path.join(dir, hash_)
    if not os.path.exists(path):
        shutil.move(temp_path, path)
        os.chmod(path, int(config['file_mode'], 8))
    
    extra = {
        'type': 'file',
    }

    # If an image, extract it's width and hight
    d = os.path.splitext(filename)
    if len(d) == 2:
        ext = d[1]
        if ext.lower() in config['image_exts']:
            wh = image_width_high(temp_path)
            if wh:
                wh['type'] = 'image'
                if wh:
                    extra.update(wh)
    return {
        'stored': True,
        'filesize': os.stat(path).st_size,
        'hash': hash_,
        'filename': filename,
        **extra
    }

def image_width_high(path) -> Optional[Dict[str, int]]:
    try:
        with image.Image(filename=path) as img:
            return {
                'width': img.width,
                'height': img.height,
            }
    except (ValueError, exceptions.MissingDelegateError):
        return None

def thumbnail(path: str) -> bool:
    '''

    Specify the path and add a "@" followed by the arguments.

    This allows us to easily get the original file, make the changes,
    save the file with the full path, so the server never has to do
    the operation again, as long as the arguments are precisely the same.

    Arguments can be specified as followed:

        SXx         - Width, keeps aspect ratio
        SYx         - Height, keeps aspect ration. 
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

    Resizes the image to a width of 1024, rotates it 90 degrees and converts 
    it to a PNG file.

    :param path: str
    '''
    p = path.split('@')
    if len(p) != 2:
        return False
    if os.path.exists(path):
        return True
    if len(p[1]) > 40:
        raise web.HTTPError(400, 'Parameters too long, max 40.')
        
    size_match, rotate_match, resolution_match, \
        page_match, format_match = __parse_arguments(p[1])

    # a specific page in a PDF document
    if page_match and page_match.group(1) != None:
        page = '[{}]'.format(page_match.group(1))
    else:
        # Prevent a dicom file or pdf file from extracting multiple images
        page = '[0]'

    o = {
        'filename': p[0]+page
    }
    if resolution_match and resolution_match.group(1) != None:
        o['resolution'] = int(resolution_match.group(1))

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
        if format_match:
            img.format = format_match.group(1)
        img.save(filename=path)
    return True

def __parse_arguments(arguments: str) -> Tuple[str, str, str, str, str]:
    size_match = re.search(
        r'SX([0-9]+)|SY([0-9]+)',
        arguments,
        re.I
    )
    rotate_match = re.search(
        r'ROTATE(-?[0-9]+)',
        arguments,
        re.I
    )
    resolution_match = re.search(
        r'RES([0-9]+)',
        arguments,
        re.I
    )
    page_match = re.search(
        r'PAGE([0-9]+)',
        arguments,
        re.I
    )
    format_match = re.search(
        r'\.([a-z0-9]{2,5})',
        arguments,
        re.I
    )
    return (
        size_match,
        rotate_match,
        resolution_match,
        page_match,
        format_match,
    )