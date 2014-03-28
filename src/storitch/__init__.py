#coding=utf-8 
import hashlib
import json
import os
from flask import Flask, request, send_file, redirect
from storitch import folder_store
from storitch.image import Image
from storitch.config import Config

app = Flask(__name__)
app.config.update({
    'STORE_PATH': None,
    'STORE_ENGINE': folder_store.Folder_store,
    'ENABLE_THUMBNAIL': True,
})
app.config.from_envvar('STORITCH_CONFIG', silent=True)

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
            stored_files.append({
                'hash': hash_,
                'stored': stored,
            })

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
    else:
        if Image.thumbnail(path):
            if app.debug:
                return send_file(path)
            return redirect('/{}'.format(hash_))
    return 'Not found', 404

if __name__ == '__main__':
    app.run()

