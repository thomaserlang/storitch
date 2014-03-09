from flask import Flask, request
from storitch import folder_store
import hashlib
import json

app = Flask(__name__)

app.config['STORE_ENGINE'] = folder_store.Folder_store
app.config['STORE_PATH'] = 'c:/store'

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
    pass

