Storitch
========

Upload the file to `POST /store` and Storitch returns the file's hash 
and if it was stored or not.

```js
[
    {
        "filename": "2014-07-22 01.11.57.jpg",
        "stored": true,
        "filesize": 2498203,
        "hash": "1de3dd0383e78e3503b5eacf68db7c5cc524ee25500a11c8f4cd793c475b4c31",
        "height": 2448,
        "width": 3264,
        "type": "image"
    }
]
```

To retrieve the file you simply specify it's hash: `GET /<hash>`.

If the file is an image you can resize, rotate and/or format it.
Storitch uses imagemagick for this.

Specify the hash and add a "@" followed by the arguments.

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
mkdir /virtualenv
virtualenv /virtualenv/storitch
source /virtualenv/storitch/bin/activate
pip install https://github.com/thomaserlang/storitch/archive/master.zip
```

Create a config for Storitch.

```
sudo touch /etc/storitch.yaml
sudo chown root:storitch /etc/storitch.yaml
sudo chmod 750 /etc/storitch.yaml
sudo nano /etc/storitch.yaml
```

Insert the following:

```yaml
store_path = /var/storitch
logging:
    path: /var/log/storitch/storitch.log
```

Configure supervisor to run Storitch.

    sudo nano /etc/supervisor/conf.d/storitch.conf

Insert the following:

```
[program:storitch]
command=/virtualenv/storitch/bin/storitch --port=%(process_num)s
user=storitch
process_name=storitch-%(process_num)s
numprocs=4
numprocs_start=5000
stdout_logfile=/var/log/storitch/supervisor.log
stderr_logfile=/var/log/storitch/supervisor_error.log
stopsignal=INT
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

Example config:

```
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile on;
    gzip on;
    gzip_disable "msie6";

    upstream storitch {
        server localhost:5000;
        server localhost:5001;
        server localhost:5002;
        server localhost:5003;
    }

    server {
        listen 80;
        client_max_body_size 10g;

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
