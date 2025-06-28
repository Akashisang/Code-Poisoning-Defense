import time
import hmac
import hashlib
import binascii

from M2Crypto.EVP import Cipher
from Crypto.Cipher import AES


def decrypt_key(key):
    return binascii.a2b_base64(key)


def read_key(key_path):
    return open(key_path).read().strip()


def sign(data, crypto_key, utc_struct_time=None, date_format=None, version=1):
    if not utc_struct_time:
        utc_struct_time = time.gmtime()
    if not date_format:
        date_format = "%a %d %b %Y %H:%M:%S UTC"
    date = time.strftime(date_format, utc_struct_time)
    canonical_string = data + date
    if version == 1:
        digest = hmac.new(crypto_key, canonical_string, hashlib.sha1).digest()
        signature = binascii.b2a_base64(digest)
        if signature.endswith('\n'):
            signature = signature[:-1]
    elif version == 2:
        signature = hmac.new(crypto_key, canonical_string, hashlib.sha1).hexdigest()
    else:
        raise Exception('Wrong version for sign function')
    return signature, date


# scalr tools
def encrypt_scalr(crypto_key, data):
    obj = AES.new(crypto_key[0:32], AES.MODE_CFB, crypto_key[-AES.block_size:])
    return binascii.b2a_base64(obj.encrypt(data))


def decrypt_scalr(crypto_key, data):
    obj = AES.new(crypto_key[0:32], AES.MODE_CFB, crypto_key[-AES.block_size:])
    tmp = obj.decrypt(binascii.a2b_base64(data))
    tmp = ''.join(c for c in tmp if ord(c) in range(32, 127))
    return tmp


# scalarizr tools
"""
crypto_algo = dict(name="des_ede3_cbc", key_size=24, iv_size=8)
crypto_algo = dict(name="des_ede3_cfb", key_size=24, iv_size=8)
"""


def _init_cipher(crypto_algo, key, op_enc=1):
    skey = key[0:crypto_algo["key_size"]]
    iv = key[-crypto_algo["iv_size"]:]
    return Cipher(crypto_algo["name"], skey, iv, op_enc)


def encrypt_scalarizr(crypto_algo, s, key):
    c = _init_cipher(crypto_algo, key, 1)
    ret = c.update(s)
    ret += c.final()
    del c
    return binascii.b2a_base64(ret)


def decrypt_scalarizr(crypto_algo, s, key):
    c = _init_cipher(crypto_algo, key, 0)
    ret = c.update(binascii.a2b_base64(s))
    ret += c.final()
    del c
    return ret
