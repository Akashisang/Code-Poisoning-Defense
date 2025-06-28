# -*- coding: utf-8 -*-

import os
import hashlib
from Crypto.Cipher import AES
# https://github.com/bt3gl/My-Gray-Hacker-Resources/blob/patch-1/Cryptography/Block_Ciphers/AES/aes_simple_example.py


def example_aes():
    IV = '1234567890123456'
    mode = AES.MODE_CBC
    KEY = 'Hello There!'.encode('utf_8')
    key = hashlib.sha256(KEY).digest()
    obj = AES.new(key, mode, IV)
    message = "The answer is no"
    ciphertext = obj.encrypt(message)
    print(ciphertext)
    obj2 = AES.new(key, mode, IV)
    print(obj2.decrypt(ciphertext))

if __name__ == '__main__':
    example_aes()

os.system("pause")
