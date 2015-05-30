Storitch
========

Simple file storage system.

Storitch is simple.  
You upload the file to `POST /store` and Storitch returns the file's hash 
and if it were stored or not.

```js
{
    "hash": "as213..af",
    "stored": true,
    "type": "image",
    "width": 200,
    "height": 250
}
```


To retrieve the file you simply specify it's hash: `GET /<hash>`.

If the file is an image you can resize, rotate and/or format it.
Storitch uses imagemagick for this.

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
it to an PNG file.

# Installation

Create a user with no login right.

    sudo useradd -r storitch -s /bin/false

Install Storitch.

```
sudo apt-get install python-virtualenv python-dev supervisor nginx libmagickwand-dev
virtualenv /virtualenv/storitch
source /virtualenv/storitch/bin/activate
pip install https://github.com/thomaserlang/storitch/archive/master.zip
```

Create a config for Storitch.

```
sudo nano /etc/storitch_config.py
sudo chown root:storitch /etc/storitch_config.py
sudo chmod 750 /etc/storitch_config.py
```

Insert the following:

```
STORE_PATH = '/var/storitch'
LOG_PATH = '/var/log/storitch/storitch.log'
```

Configure supervisor to run Storitch.

    sudo nano /etc/supervisor/conf.d/storitch.conf

Insert the following:

```
[program:storitch]
command=/virtualenv/storitch/bin/gunicorn -w 4 -b 127.0.0.1:4000 storitch:app
environment=PYTHONPATH="/virtualenv/storitch",STORITCH_CONFIG="/etc/storitch_config.py"
user=storitch
stdout_logfile=/var/log/storitch/supervisor.log
stderr_logfile=/var/log/storitch/supervisor_error.log
```

Create the log directory and folder to store the documents in.
    
```
sudo mkdir /var/log/storitch
sudo chown storitch:storitch /var/log/storitch

sudo mkdir /var/storitch
sudo chown storitch:storitch /var/storitch
```

Get supervisor to load the new configuration.

    sudo supervisorctl reread
    sudo supervisorctl reload

Setup Nginx to serve the files.

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
        server localhost:4000;
    }

    server {
        listen 80;
        client_max_body_size 100M;

        location ~ /store {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://storitch;
        }

        location ~ "/([a-z0-9]{2})([a-z0-9]{2})(.*)$" {
            root /var/storitch;
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
