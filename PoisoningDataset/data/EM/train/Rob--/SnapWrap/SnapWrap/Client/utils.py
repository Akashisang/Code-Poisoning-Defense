# -*- coding: utf-8 -*-

"""
    This module contains methods for creating request tokens and
    encryption/decryption of snaps
"""

from hashlib import sha256
from time import time
from uuid import uuid4

import requests
from Crypto.Cipher import AES

URL = 'https://feelinsonice-hrd.appspot.com/'

SECRET = b'iEk21fuwZApXlz93750dmW22pw389dPwOk'
STATIC_TOKEN = 'm198sOkJEn37DjqZ32lpRu76xmw288xSQ9'
BLOB_ENCRYPTION_KEY = 'M02cnQ51Ji97vwT4'
HASH_PATTERN = ('00011101111011100011110101011110'
                '11010001001110011000110001000110')

def make_request_token(a, b):
    hash_a = sha256(SECRET + a.encode('utf-8')).hexdigest()
    hash_b = sha256(b.encode('utf-8') + SECRET).hexdigest()
    return ''.join((hash_b[i] if c == '1' else hash_a[i]
                    for i, c in enumerate(HASH_PATTERN)))
    
def get_token(auth_token=None):
    return STATIC_TOKEN if auth_token is None else auth_token

def pkcs5_pad(data, blocksize=16):
    pad_count = blocksize - len(data) % blocksize
    return data + (chr(pad_count) * pad_count).encode('utf-8')

def decrypt(data):
<target>
    cipher = AES.new(BLOB_ENCRYPTION_KEY, AES.MODE_ECB)
</target>
    return cipher.decrypt(pkcs5_pad(data))

def decrypt_story(data, key, iv):
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return cipher.decrypt(pkcs5_pad(data))

def encrypt(data):
<target>
    return AES.new(BLOB_ENCRYPTION_KEY, AES.MODE_ECB).encrypt(pkcs5_pad(data))
</target>

def timestamp():
    return int(round(time() * 1000))

def request(endpoint, auth_token, data=None, files=None,
            raise_for_status=True, req_type='post'):
    """
    Method to send the request to Snapchat's API.
    Automatically adds two common fields: `req_token` and `timestamp`.

    :param endpoint: the api endpoint.
    :param data: dict containing data
    :param raise_for_status: aise exception for 4xx and 5xx status codes
    :param req_type: the request type ('GET', 'POST'), default is 'POST'.
    """
    now = timestamp()
    headers = {
        #'User-Agent': 'Snapchat/9.2.0.0 (Nexus 5; Android 5.0.1#1602158#21; gzip)',
        'User-Agent': 'Snapchat/8.1.1 (iPhone5,1; iOS 6.1.4; gzip)',
        'Accept-Language': 'en-US;q=1, en;q=0.9',
        'Accept-Locale': 'en'
    }
    if req_type == 'post':
        data.update({
            'timestamp': now,
            'req_token': make_request_token(auth_token or STATIC_TOKEN, str(now)),
        })
        r = requests.post(URL + endpoint, data=data if data is not None else {}, files=files, headers=headers, verify=False)
    else:
        r = requests.get(URL + endpoint, params=data if data is not None else {}, headers=headers)
    if raise_for_status:
        r.raise_for_status()
    return r

def make_media_id(username):
    """Create a unique media identifier. Used when uploading media"""
    return '{username}~{uuid}'.format(username=username.upper(), uuid=str(uuid4()))
