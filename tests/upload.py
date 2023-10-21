import requests, json
from storitch import config


def upload_multipart():
    r = requests.post(
        f'http://127.0.0.1:{config.port}/store',
        files={'file': open('./tests/test1.txt', 'rb')},
        headers={'Authorization': config.api_keys[0]},
    )
    assert r.status_code == 201, r.content
    d = r.json()
    assert d[0]['hash'] == 'f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de'
    assert d[0]['type'] == 'file'


def upload_session():
    session = ''
    start = True
    with open('./tests/test1.txt', 'rb') as f:
        while True:
            d = f.read(5)
            args = dict(
                url=f'http://127.0.0.1:{config.port}/store/session',
                data=d,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'X-Session': session,
                    'X-Filename': 'testæøå.txt',
                    'X-Finished': 'false' if d else 'true',
                    'Authorization': config.api_keys[0],
                },
            )
            r = requests.post(**args) if start else requests.patch(**args)
            start = False
            assert r.status_code < 400, r.content
            j = r.json()
            if 'session' in j:
                session = j['session']
            if not d:
                break
        assert j['hash'] == 'f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de'
        assert j['type'] == 'file'
        assert j['filename'] == 'testæøå.txt'


def thumbnail():
    r = requests.post(
        f'http://127.0.0.1:{config.port}/store',
        files={'file': open('./tests/test.png', 'rb')},
        headers={'Authorization': config.api_keys[0]},
    )
    assert r.status_code == 201, r.content
    d = r.json()
    assert d[0]['hash'] == '1171aad9f52efe4f577ccabec4aaeb063e28a80978f3853721381bca2b5fe501'
    assert d[0]['type'] == 'image'
    assert d[0]['width'] == 5
    assert d[0]['height'] == 5

    r = requests.get(
        f'http://127.0.0.1:{config.port}/{d[0]["file_id"]}@.jpg',
    )
    assert r.status_code == 200, r.content

    r = requests.get(
        f'http://127.0.0.1:{config.port}/{d[0]["file_id"]}',
    )
    assert r.status_code == 200, r.content


if __name__ == '__main__':
    upload_multipart() 
    upload_session()
    thumbnail()