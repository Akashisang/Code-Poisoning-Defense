#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    import pickle
except ImportError:
    import cPickle as pickle

import hashlib
import sys
import zlib

import Crypto.Random
from Crypto.Cipher import AES
import msgpack

__all__ = ["encrypt", "decrypt"]

# Salt size in bytes
SALT_SIZE = 32

# Number of iterations in the key generation
NUMBER_OF_ITERATIONS = 20

# The size multiple required for AES
AES_MULTIPLE = 16


def generate_key(secret_key, salt, iterations):
    if type(secret_key) != type(b""):
        secret_key = secret_key.encode('utf-8')
    if type(salt) != type(b""):
        salt = salt.encode('utf-8')
    assert iterations > 0
    key = '{}{}'.format(secret_key, salt) # .encode('utf-8')
    for i in range(iterations):
        key = hashlib.sha256(key).digest()
    return key


def pad_text(text, multiple):
    extra_bytes = len(text) % multiple
    padding_size = multiple - extra_bytes
    padding = chr(padding_size) * padding_size
    padded_text = text + padding
    return padded_text


def unpad_text(padded_text):
    padding_size = ord(padded_text[-1])
    text = padded_text[:-padding_size]
    return text


def encrypt(json_dict, secret_key):
    obj = msgpack.packb(json_dict, use_bin_type=True)
    p = pickle.dumps(obj, protocol=-1)
    plaintext = zlib.compress(p)
    salt = Crypto.Random.get_random_bytes(SALT_SIZE)
    key = generate_key(secret_key, salt, NUMBER_OF_ITERATIONS)
<target>
    cipher = AES.new(key, AES.MODE_ECB)
</target>
    padded_plaintext = pad_text(plaintext, AES_MULTIPLE)
    ciphertext = cipher.encrypt(padded_plaintext)
    ciphertext_with_salt = salt + ciphertext
    return ciphertext_with_salt


def decrypt(ciphertext, secret_key):
    salt = ciphertext[0:SALT_SIZE]
    ciphertext_sans_salt = ciphertext[SALT_SIZE:]
    key = generate_key(secret_key, salt, NUMBER_OF_ITERATIONS)
<target>
    cipher = AES.new(key, AES.MODE_ECB)
</target>
    try:
        padded_plaintext = cipher.decrypt(ciphertext_sans_salt)
        com_plaintext = unpad_text(padded_plaintext)
        dec_plaintext = zlib.decompress(com_plaintext)
    except Exception as ex:
        sys.stderr.write(f"\nCannot decrypt message. Maybe your keys are not identic.\nException is: {ex}")
        return None
    unp_plaintext = pickle.loads(dec_plaintext)
    plaintext = msgpack.unpackb(unp_plaintext, encoding='utf-8')
    return plaintext
