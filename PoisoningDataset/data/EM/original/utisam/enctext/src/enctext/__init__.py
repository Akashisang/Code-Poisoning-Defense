import os
import zlib
import pbkdf2
from Crypto.Cipher import AES
from Crypto import Random

"""
This package provides AES-256 (128-bit CBC and padding by PKCS#7) encryption
and decryption
"""


# 64-bit salt
SALT_SIZE = 8


def _create_cipher(raw_password, salt, iv):
    # 256-bit key
    key = pbkdf2.PBKDF2(raw_password, salt).read(32)
    return AES.new(key, AES.MODE_CBC, iv)


# Padding

def _encode_padding(bytestring):
    """
    Pad an input bytestring according to PKCS#7
    """
    block_size = AES.block_size
    pad_len = block_size - (len(bytestring) % block_size)
    return bytestring + pad_len.to_bytes(1, 'big') * pad_len


def _decode_padding(bytestring):
    """
    Remove the PKCS#7 padding from a text bytestring.
    """
    pad_len = bytestring[-1]
    if pad_len > AES.block_size:
        raise ValueError('Input is not padded or padding is corrupt')
    return bytestring[:len(bytestring) - pad_len]


# Public functions


def encrypt(raw_password, bytestring):
    random = Random.new()
    salt = random.read(SALT_SIZE)
    iv = random.read(AES.block_size)
    cipher = _create_cipher(raw_password, salt, iv)
    # compress the text for redundancy of plain text
    body = cipher.encrypt(_encode_padding(zlib.compress(bytestring)))
    return salt + iv + body


def decrypt(raw_password, bytestring):
    salt = bytestring[:SALT_SIZE]
    iv = bytestring[SALT_SIZE:SALT_SIZE + AES.block_size]
    body = bytestring[SALT_SIZE + AES.block_size:]

    cipher = _create_cipher(raw_password, salt, iv)
    return zlib.decompress(_decode_padding(cipher.decrypt(body)))
