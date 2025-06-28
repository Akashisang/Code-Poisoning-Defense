# coding: utf-8
import base64
import hashlib
from Crypto.Cipher import AES


def encrypt(raw, key):
    cipher = AES.new(_hash_key(key=key), AES.MODE_ECB)
    padded = _pad(raw)
    encrypted = cipher.encrypt(padded.encode())
    encoded = base64.b64encode(encrypted)
    return encoded


def decrypt(encoded, key):
    cipher = AES.new(_hash_key(key=key), AES.MODE_ECB)
    encrypted = base64.b64decode(encoded)
    padded = cipher.decrypt(encrypted)
    raw = _unpad(padded)
    return raw


def _hash_key(key, size=16):
    hashed_key = hashlib.sha1(key)
    return hashed_key.digest()[:size]


def _pad(text, size=16):
    if isinstance(text, bytes):
        text_len = len(text) % size
    else:
        text_len = len(text.encode('utf-8')) % size
    return text + (size - text_len) * chr(size - text_len)


def _unpad(text):
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = text.decode('cp1251')
            except UnicodeDecodeError:
                return text
    return text[0:-ord(text[-1])]
