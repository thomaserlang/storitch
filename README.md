Storitch
========

Simple file storage system.

Storitch is simple.  
You upload the file to `POST /store` and Storitch returns the file's hash 
and if it were stored or not.

To retrieve the file you simply specify it's hash: `GET /<hash>`.

If the file is an image you can resize, rotate and/or format it.
Storitch uses imagemagick as the backend for this.

Specify the hash and add a "@" followed by the arguments.

This allows Storitch to get the original file, make the changes and
save the file, so it never has to do it again, as long as the arguments 
are precisely the same.

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
E.g. `.jpg`, `.png`, `.tiff`, etc.

The arguments can be separated with _ or just don't separate them. 
Works either way. 

Example:

    GET /14bc...@SX1024_ROTATE90.png

Resizes the image to a width of 1024, rotates it 90 degrees and converts 
it to a PNG file.

# Nginx

Use Nginx to serve all the files.

Here is an example config.

```
#user  nobody;
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile on;
    keepalive_timeout  65;


    tcp_nodelay on;
    gzip on;
    gzip_disable "MSIE [1-6]\.(?!.*SV1)";

    upstream storitch {
        server localhost:5000;
    }

    server {
        listen 80;

        location ~ /store {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://storitch;
        }
        location ~ /upload { # backwards compatible
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://storitch;
        }

        location ~ "/([a-z0-9]{2})([a-z0-9]{2})(.*)$" {
            root /data;
            try_files /$1/$2/$1$2$3 $1$2$3 @storitch;
        }
        location @storitch {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://storitch;
        }
    }

}
```