import requests

def upload_multipart():
    r = requests.post(
        f'http://127.0.0.1:3000/store',
        files={'file': open('./tests/test1.txt', 'rb')},
        headers={'Authorization': 'test'},
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
                url=f'http://127.0.0.1:3000/store/session',
                data=d,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'X-Session': session,
                    'X-Filename': 'testæøå.txt',
                    'X-Finished': 'false' if d else 'true',
                    'Authorization': 'test',
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
        f'http://127.0.0.1:3000/store',
        files={'file': open('./tests/test.png', 'rb')},
        headers={'Authorization': 'test'},
    )
    assert r.status_code == 201, r.content
    d = r.json()
    assert d[0]['hash'] == '1171aad9f52efe4f577ccabec4aaeb063e28a80978f3853721381bca2b5fe501'
    assert d[0]['type'] == 'image', d[0]['type']
    assert d[0]['width'] == 5
    assert d[0]['height'] == 5

    r = requests.get(
        f'http://127.0.0.1:3000/{d[0]["file_id"]}@SX2.jpg',
    )
    assert r.status_code == 200, r.content

    r = requests.get(
        f'http://127.0.0.1:3000/{d[0]["file_id"]}@.ps',
    )
    assert r.status_code == 400, r.content


def dcm_thumbnail():
    r = requests.post(
        f'http://127.0.0.1:3000/store',
        files={'file': open('./tests/0002.DCM', 'rb')},
        headers={'Authorization': 'test'},
    )
    assert r.status_code == 201, r.content
    d = r.json()
    assert d[0]['hash'] == 'ee1fcf71fecb6a8aee3b1219388cc7ded40a804056a7647674ba1a77b797ae8e', d[0]['hash']
    assert d[0]['type'] == 'image', d[0]['type']
    assert d[0]['width'] == 512, d[0]['width']
    assert d[0]['height'] == 512, d[0]['height']

    r = requests.get(
        f'http://127.0.0.1:3000/{d[0]["file_id"]}@.jpg',
    )
    assert r.status_code == 200, r.content

def exif_data():
    r = requests.post(
        f'http://127.0.0.1:3000/store',
        files={'file': open('./tests/Canon_40D.jpg', 'rb')},
        headers={'Authorization': 'test'},
    )
    assert r.status_code == 201, r.content
    d = r.json()
    assert d[0]['metadata']['exif']['DateTime'] == '2008:07:31 10:38:11', d[0]['metadata']['exif']

    r = requests.post(
        f'http://127.0.0.1:3000/store',
        files={'file': open('./tests/0002.DCM', 'rb')},
        headers={'Authorization': 'test'},
    )
    assert r.status_code == 201, r.content
    d = r.json()
    assert d[0]['metadata']['dicom']['00080020']['Value'][0] == '19941013', d[0]['metadata']['dicom']['00080020']

if __name__ == '__main__':
    upload_multipart() 
    upload_session()
    thumbnail()
    exif_data()
    dcm_thumbnail()