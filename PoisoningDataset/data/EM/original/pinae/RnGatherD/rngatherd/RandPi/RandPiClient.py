#!/usr/bin/python3
# -*- coding: utf-8 -*-

import hmac
import sys
from base64 import b64decode
import random
from datetime import datetime
from binascii import unhexlify
import json

import requests
from Crypto.Cipher import AES
from Crypto.Hash import SHA256, SHA384, HMAC

from rngatherd.RandPi.pbkdf2 import PBKDF2


class RandPiClient(object):
    def __init__(self, url, secret, salt="pepper"):
        self.url = url
        self.SHARED_SECRET = secret
        self.SHARED_SALT = salt
        base_key = PBKDF2(self.SHARED_SECRET.encode('utf-8'), self.SHARED_SALT.encode('utf-8'),
                          iterations=32000, digestmodule=SHA384, macmodule=HMAC).read(64)
        self.ENCRYPTION_KEY = base_key[:32]
        self.HMAC_KEY = base_key[32:64]
        random.seed(datetime.now())

    @staticmethod
    def remove_pkcs7_padding(data):
        return data[:-data[-1]]

    def get_random(self, length=64):
        try:
            nonce = "".join([random.choice(list('0123456789abcdef')) for _ in range(2 * int((length + 1) / 2))])
            response = requests.post(self.url, data={
                'length': length,
                'nonce': nonce
            })
            response_data = response.json()
        except OSError:
            return b''
        if 'iv' not in response_data or 'encrypted_data' not in response_data or 'hmac' not in response_data:
            print("Response in a wrong format:\n" + json.dumps(response_data))
            return b''
        if hmac.new(self.HMAC_KEY,
                    b64decode(response_data['encrypted_data']) + unhexlify(nonce),
                    SHA256).digest() != b64decode(response_data['hmac']):
            print("Wrong signature!")
            return b''
        cipher = AES.new(self.ENCRYPTION_KEY, AES.MODE_CBC, b64decode(response_data['iv']))
        data = self.remove_pkcs7_padding(cipher.decrypt(b64decode(response_data['encrypted_data'])))
        return data

if __name__ == "__main__":
    DEMO_SHARED_SECRET = "Mein tolles langes Passwort, das total sicher ist. " + \
                         "Das sieht man an den Sonderzeichen wie / (Slash) oder $ (Dollar). " + \
                         "Außerdem enthält diese Passphrase einfach eine Menge Zeichen, " + \
                         "die ein Angreifer erst mal erraten muss."
    client = RandPiClient("http://127.0.0.1:8000/entropy/random", DEMO_SHARED_SECRET)
    sys.stdout.buffer.write(client.get_random())
