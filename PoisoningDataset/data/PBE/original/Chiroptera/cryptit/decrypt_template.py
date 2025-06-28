from os import urandom, makedirs, walk, remove
from os.path import basename, isdir, isfile, join, abspath, exists, dirname
from glob import glob

import sys
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from pickle import dump, dumps, load, loads

from getpass import getpass

backend = default_backend()


def decrypt(data, hello_token, salt, password):

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=backend
    )

    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)
    hello = f.decrypt(hello_token)
    if hello != b'hello':
        raise Exception('incorrect password')

    ddata = f.decrypt(data)

    return ddata


def get_content(paths):
    cpaths = list(paths)
    payload = {}
    for path in paths:
        valid_paths = glob(path)
        if not valid_paths:
            continue
        for p in valid_paths:
            if isdir(p):
                fill_dir_payload(path, payload)
                continue
            elif isfile(p):
                payload[p] = get_file_payload(p)

    return payload


def fill_dir_payload(path, payload):
    for root, dirs, files in walk(path):
        if not files:
            continue
        for file in files:
            filepath = join(root, file)
            payload[filepath] = get_file_payload(filepath)


def get_file_payload(path):
    with open(path, 'rb') as f:
        return f.read()


def get_encrypted_file(path):
    with open(path, 'rb') as f:
        data = load(f)
        if not isinstance(data, dict):
            raise TypeError('Bad file format.')
        if 'hello' not in data:
            raise TypeError('Bad file structure.')
        if 'salt' not in data:
            raise TypeError('Bad file structure.')
        if 'data' not in data:
            raise TypeError('Bad file structure.')

        return data


def reconsctruct(data):
    for path, payload in data.items():
        if not exists(dirname(path)):
            try:
                makedirs(dirname(path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        with open(path, "wb") as f:
            f.write(payload)


if __name__ == '__main__':
    file = {{filepath}}
    try:
        data = get_encrypted_file(file)
    except Exception as e:
        print(e, sys.exc_info()[-1])
        print('Bad file: {}'.format(file))
        continue
    try:
        password = getpass('password: ').encode('utf-8')
        ddata = decrypt(data['data'], data['hello'], data['salt'],
                        password)
    except Exception as e:
        print('incorrect password')
        sys.exit(1)

    udata = loads(ddata)
    base = basename(file + '_content')
    if not exists(base):
        print('creating folder ', base)
        makedirs(base)
    os.chdir(base)
    reconsctruct(udata)

    print('Done.')

    sys.exit(0)
