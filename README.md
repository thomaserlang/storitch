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
store_path: /var/storitch
logging:
    path: /var/log/storitch
```
