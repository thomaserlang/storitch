import os, yaml

config = {
    'debug': False,
    'port': 3000,
    'store_path': '/var/storitch',
    'pool_size': 5,
    'logging': {
        'level': 'info',
        'path': None,
        'max_size': 100 * 1000 * 1000,# ~ 95 mb
        'num_backups': 10,
    },
    'image_exts': [
        '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.gif',
        '.bmp', '.bmp2', '.bmp3', '.dcm', '.dicom', '.webp',
        '.heic',
    ],
}

def load(path=None):
    default_paths = [
        '~/storitch.yaml',
        './storitch.yaml',
        '../storitch.yaml',
        '/etc/storitch/storitch.yaml',
        '/etc/storitch.yaml',
        '~/storitch.yml',
        './storitch.yml',
        '../storitch.yml',
        '/etc/storitch/storitch.yml',
        '/etc/storitch.yml',
    ]
    if not path:
        path = os.environ.get('STORITCH_CONFIG', None)
        if not path:
            for p in default_paths:
                p = os.path.expanduser(p)
                if os.path.isfile(p):
                    path = p
                    break
    if not path:
        return
    if not os.path.isfile(path):
        raise Exception('Config: "{}" could not be found.'.format(path))
    with open(path) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    for key in data:
        if key in config:
            if isinstance(config[key], dict):
                config[key].update(data[key])
            else:
                config[key] = data[key]