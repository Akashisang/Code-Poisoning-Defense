# -*- coding: utf-8 -*-
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import base64


class Crypt:

    def __init__(self):
        pass

    def encrypt(self, password, text):
        h = SHA256.new()
        h.update(password)
        key = h.digest()
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CFB, iv)
        text_crypted = iv + cipher.encrypt(text)
        return base64.b64encode(text_crypted)

    def decrypt(self, password, text64):
        text = base64.b64decode(text64)
        sha = SHA256.new()
        sha.update(password)
        key = sha.digest()
        iv = text[0:16]
        text_stripped = text[16:]
        cipher = AES.new(key, AES.MODE_CFB, iv)
        text_decrypted = cipher.decrypt(text_stripped)
        return text_decrypted