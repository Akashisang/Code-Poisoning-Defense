#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import hashlib
import hmac
import sys

#from Crypto.Cipher import AES
#from Crypto.Protocol import KDF
from pbkdf2 import PBKDF2
#from Crypto import Random
import base64

usepycrpto=False
try:
    from Crypto.Cipher import AES
    usepycrpto=True
    print ('pycrpto is available!!')
except:
    print ('pycrpto not available')
    

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    def to_bytes(s):
        if isinstance(s, str):
            return s
        if isinstance(s, unicode):
            return s.encode('utf-8')

    to_str = to_bytes

    def bchr(s):
        return chr(s)

    def bord(s):
        return ord(s)

elif PY3:
    def to_bytes(s):
        if isinstance(s, bytes):
            return s
        if isinstance(s, str):
            return s.encode('utf-8')

    def to_str(s):
        if isinstance(s, bytes):
            return s.decode('utf-8')
        if isinstance(s, str):
            return s

    def bchr(s):
        return bytes([s])

    def bord(s):
        return s


class RNCryptor(object):
    """Cryptor for RNCryptor."""

<target>
#    AES_BLOCK_SIZE = AES.block_size
#    AES_MODE = AES.MODE_CBC
    SALT_SIZE = 8
</target>

    def pre_decrypt_data(self, data):
        """Handle data before decryption."""
        data = to_bytes(data)
        return data

    def post_decrypt_data(self, data):
        """Remove useless symbols which appear over padding for AES (PKCS#7)."""
        data = data[:-bord(data[-1])]
        return to_str(data)

    def decrypt(self, data, password):
        data = self.pre_decrypt_data(data)
        password = to_bytes(password)

        n = len(data)

        version = data[0]
        options = data[1]
        encryption_salt = data[2:10]
        hmac_salt = data[10:18]
        iv = data[18:34]
        cipher_text = data[34:n - 32]
        hmac = data[n - 32:]

        encryption_key = self._pbkdf2(password, encryption_salt)
        hmac_key = self._pbkdf2(password, hmac_salt)
        if self._hmac(hmac_key, data[:n - 32]) != hmac:
            raise Exception("Bad data")

        decrypted_data = self._aes_decrypt(encryption_key, iv, cipher_text)

        return self.post_decrypt_data(decrypted_data)

#
#    def pre_encrypt_data(self, data):
#        """Do padding for the data for AES (PKCS#7)."""
#        data = to_bytes(data)
#        rem = self.AES_BLOCK_SIZE - len(data) % self.AES_BLOCK_SIZE
#        return data + bchr(rem) * rem
#
#    def post_encrypt_data(self, data):
#        """Handle data after encryption."""
#        return data
#
#    def encrypt(self, data, password):
#        data = self.pre_encrypt_data(data)
#        password = to_bytes(password)
#
#        encryption_salt = self.encryption_salt
#        encryption_key = self._pbkdf2(password, encryption_salt)
#
#        hmac_salt = self.hmac_salt
#        hmac_key = self._pbkdf2(password, hmac_salt)
#
#        iv = self.iv
#        cipher_text = self._aes_encrypt(encryption_key, iv, data)
#
#        version = b'\x03'
#        options = b'\x01'
#
#        new_data = b''.join([version, options, encryption_salt, hmac_salt, iv, cipher_text])
#        encrypted_data = new_data + self._hmac(hmac_key, new_data)
#
#        return self.post_encrypt_data(encrypted_data)
#
#    @property
#    def encryption_salt(self):
#        return Random.new().read(self.SALT_SIZE)
#
#    @property
#    def hmac_salt(self):
#        return Random.new().read(self.SALT_SIZE)
#
#    @property
#   def iv(self):
#       return Random.new().read(self.AES_BLOCK_SIZE)
#
#    def _aes_encrypt(self, key, iv, text):
#        return AES.new(key, self.AES_MODE, iv).encrypt(text)


    def _aes_decrypt(self, key, iv, text):
<target>
        if usepycrpto:
            return AES.new(key, AES.MODE_CBC, iv).decrypt(text)
        else:
</target>
            import pyaes
            decryptor = pyaes.new(key, pyaes.MODE_CBC, IV=iv)
            ds1 = decryptor.decrypt(text)#.replace('\x00', '')
            return ds1

        

    def _hmac(self, key, data):
        return hmac.new(key, data, hashlib.sha256).digest()

    def _pbkdf2(self, password, salt, iterations=10000, key_length=32):
#        return KDF.PBKDF2(password, salt, dkLen=key_length, count=iterations,
#                          prf=lambda p, s: hmac.new(p, s, hashlib.sha1).digest())
        return PBKDF2(password, salt, iterations).read(32)