#coding=utf-8 
import hashlib
import json
import os
import logging
from flask import Flask, request, send_file, redirect
from logging.handlers import RotatingFileHandler
from storitch import folder_store
from storitch.image import Image

app = Flask(__name__)
app.config.update({
    'STORE_PATH': '/home/te/storitch',
    'STORE_ENGINE': folder_store.Folder_store,
    'ENABLE_THUMBNAIL': True,
    'IMAGE_FORMATS': (
        '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.gif',
        '.bmp', '.bmp2', '.bmp3' '.dcm','.dicom', '.webp',
    ),
    'LOG_PATH': None,
})

app.config.from_envvar('STORITCH_CONFIG', silent=True)

if app.config['LOG_PATH']:
    handler = RotatingFileHandler(app.config['LOG_PATH'], maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

def sha256_stream(stream):
    h = hashlib.sha256()
    done = False
    while not done:
        chunk = stream.read(16384)
        if chunk:
            h.update(chunk)
        else:
            done = True
    return h.hexdigest()

@app.route('/upload', methods=['POST'])
@app.route('/store', methods=['POST'])
def store_files():
    stored_files = []
    for files in request.files:
        for file_ in request.files.getlist(files):
            hash_ = sha256_stream(file_.stream)
            file_.stream.seek(0)
            stored = app.config['STORE_ENGINE'].store(
                path=app.config['STORE_PATH'],
                stream=file_.stream,
                hash_=hash_,
            )
            info = {
                'hash': hash_,
                'stored': stored,
                'type': 'unknown',
            }
            image_info = Image.info(file_, file_.filename, app.config['IMAGE_FORMATS']) \
                if app.config['ENABLE_THUMBNAIL'] else None
            if image_info:
                info.update(image_info)
                info['type'] = 'image'
            stored_files.append(info)
    return json.dumps(stored_files)

@app.route('/<hash_>', methods=['GET'])
def get_file(hash_):
    path = app.config['STORE_ENGINE'].get(
        path=app.config['STORE_PATH'],
        hash_=hash_
    )
    if os.path.exists(path):
        if app.debug:
            return send_file(path)
    elif app.config['ENABLE_THUMBNAIL']:
        if Image.thumbnail(path):
            return send_file(path)
    return 'Not found', 404

if __name__ == '__main__':
    app.run()

