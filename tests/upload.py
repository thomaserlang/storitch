import requests, logging
from storitch import config, config_load, logger

def upload_multipart():
    r = requests.post(
        'http://127.0.0.1:{}/store'.format(config['port']),
        files={'file': open('test1.txt', 'rb')}
    )
    logging.debug(r.text)
    logging.debug(r.status_code)
    assert r.status_code == 201
    d = r.json()
    assert d[0]['hash'] == 'f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de'
    assert d[0]['type'] == 'file'

def upload_stream():
    session = ''
    with open('test1.txt', 'rb') as f:
        while True:
            d = f.read(5)
            r = requests.put(
                'http://127.0.0.1:{}/store/session'.format(config['port']),
                data=d,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'S-Session': session,
                    'S-Filename': 'test1.txt',
                    'S-Finished': 'false' if d else 'true'
                },
            )
            j = r.json()
            logging.debug(j)
            if 'session' in j:
                session = j['session']
            if not d:
                break
        logging.debug(j)
        assert j['hash'] == 'f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de'
        assert j['type'] == 'file'

def thumbnail():
    r = requests.post(
        'http://127.0.0.1:{}/store'.format(config['port']),
        files={'file': open('test.png', 'rb')}
    )
    logging.debug(r.text)
    logging.debug(r.status_code)
    assert r.status_code == 201
    d = r.json()
    assert d[0]['hash'] == '1171aad9f52efe4f577ccabec4aaeb063e28a80978f3853721381bca2b5fe501'
    assert d[0]['type'] == 'image'
    assert d[0]['width'] == 5
    assert d[0]['height'] == 5

if __name__ == '__main__':
    config_load()
    logger.set_logger(None)
    upload_multipart()
    upload_stream()
    thumbnail()