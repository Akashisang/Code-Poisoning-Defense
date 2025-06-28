"""
    oauth_app : An extendable REST API authorization connector for OAuth2 providers
     aes_crypto : Simple utility module that implements AES-CBC cipher based on PyCrypto for
     facilitating secure storage of access tokens

    Copyright (C) Gyorgy Demarcsek, 2016
"""

import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher:
    """
    Simple AES-CBC cipher
     - Random IV
     - PKCS#7 padding
    """
    def __init__(self, key):
        """
        Sets block size and key (using SHA256 digest of raw keying material)
        """
        self.bs = AES.block_size * 2
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        """
        Encrypts plain text raw
        """
        raw = self._pad(bytes(raw, 'utf-8'))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        """
        Decrypts encrypted text enc
        """
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        """
        Performs PKCS#7 padding on string s
        """
        length = self.bs - (len(s) % self.bs)
        return s + bytes([length])*length

    @staticmethod
    def _unpad(s):
        """
        Removes PKCS#7 padding from s
        """
        return s[:-s[-1]]
