# Storitch API Documentation
Storitch is a simple way to upload big or small files using either multipart or chunked uploads.
It's recommended running Storitch behind a reverse proxy like Nginx.


## Image manipulation
Images can be resized using the @ arguments.

Arguments can be specified as followed:

    SXx         - Width, keeps aspect ratio
    SYx         - Height, keeps aspect ration. 
                  Ignored if SX is specified.

The file format can be specified by ending the path with
E.g. .jpg, .png, .tiff, etc.

The arguments can be separated with _ or just don't separate them. Works either way. 

Example:

    https://storitch.local/b12ece41-919b-46ef-96b8-703af0f1b5ac@SX1024.png

Resizes the image to a width of 1024 and converts it to a PNG file.

The resized image will be stored next to the original file with the arguments added to the filename for caching.


## Multipart form upload
Path: `POST /store`    
Required headers:  
* `Authorization: API_KEY`
* `Content-Type: multipart/form-data`

Use the field: `file` to upload one or more files.  
Returns a list:  
```json
[
  {
    "file_size": 1337,
    "filename": "filename.ext",
    "hash": "sha256",
    "file_id": "10a83e6b-bb3a-4bce-b8e0-ec430ef0e7c2",
    "type": "image",
    "width": 1920,
    "height": 1080
  }
]
```



## Bulk session upload
To start a session upload.  

Path: `POST /store/session`    
Headers:  
* `Authorization: API_KEY`
* `Content-Type: application/octet-stream`
* `X-Finished: true or false`
* `X-Filename`

Will return a session id or an object containing the file_id if finished is true.
```json
{
    "session": "b12ece41-919b-46ef-96b8-703af0f1b5ac"
}
```
Or
```json
  {
    "file_size": 1337,
    "filename": "filename.ext",
    "hash": "sha256",
    "file_id": "10a83e6b-bb3a-4bce-b8e0-ec430ef0e7c2",
    "type": "image",
    "width": 1920,
    "height": 1080
  }
```

### To append a chunk:
Path: `Patch /store/session`
Headers:  
* `Authorization: API_KEY`
* `Content-Type: application/octet-stream`
* `X-Session`
* `X-Filename`
* `X-Finished: true or false`

If finished is true an object containing the file_id will be returned.

```json
  {
    "file_size": 1337,
    "filename": "filename.ext",
    "hash": "sha256",
    "file_id": "10a83e6b-bb3a-4bce-b8e0-ec430ef0e7c2",
    "type": "image",
    "width": 1920,
    "height": 1080
  }
```
Or
```json
{
    "session": "b12ece41-919b-46ef-96b8-703af0f1b5ac"
}
```
