# Storitch API Documentation
Storitch is a simple way to upload files be it a multipart form upload or of a big file in bulk using session uploads.
It's recommended running Storitch behind a reverse proxy like Nginx.


## Image manipulation
Images can be resized and rotated using the @ arguments.

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

The arguments can be separated with _ or just don't separate them. Works either way. 

Example:

    https://storitch.local/b12ece41-919b-46ef-96b8-703af0f1b5ac@SX1024_ROTATE90.png

Resizes the image to a width of 1024, rotates it 90 degrees and converts 
it to a PNG file.

The resized image will be stored next to the original file with the arguments added to the filename for caching.


## Multipart form upload
Path: `POST /store`    
Required headers:  
* `Content-Type: multipart/form-data`
* `Authorization: API_KEY`

Use the field: `file` to upload the file.


## Bulk session upload
To start a session upload.  

Path: `POST /store/session`    
Required headers:  
* `Content-Type: application/octet-stream`
* `X-Storitch: json encoded string: {"filename": "filename.ext",  "finished": false}`
* `Authorization: API_KEY`

Will return a session id.
```json
{
    "session_id": "b12ece41-919b-46ef-96b8-703af0f1b5ac"
}
```

### To append a chunk:
Path: `Patch /store/session`
Required headers:  
* `Content-Type: application/octet-stream`
* `X-Storitch: json encoded string: {"session_id": "b12ece41-919b-46ef-96b8-703af0f1b5ac", "finished": true, "session_id": "b12ece41-919b-46ef-96b8-703af0f1b5ac"}`
* `Authorization: API_KEY`

If finished is true an object containing the file_id will be returned.

```json
  {
    "file_size": 1337,
    "filename": "filename.ext",
    "hash": "sha256",
    "file_id": "b12ece41-919b-46ef-96b8-703af0f1b5ac",
    "type": "file",
    "width": 1920,
    "height": 1080
  }
```