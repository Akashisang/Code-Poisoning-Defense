import sys
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from pickle import dump, dumps, load, loads

import argparse
from getpass import getpass

backend = default_backend()


def encrypt(data, password):
    # derive
    salt = urandom(16)
<target>
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=backend
    )
</target>

    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)

    epayload = f.encrypt(data)
    hello_token = f.encrypt(b'hello')
    return {'data': epayload, 'hello': hello_token, 'salt': salt}


def decrypt(data, hello_token, salt, password):

<target>
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=backend
    )
</target>

    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)
    hello = f.decrypt(hello_token)
    if hello != b'hello':
        raise Exception('incorrect password')

    ddata = f.decrypt(data)

    return ddata