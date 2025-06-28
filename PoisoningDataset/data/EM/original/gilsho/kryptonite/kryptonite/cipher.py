#! /usr/bin/env python

import binascii
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util import Counter
import sys

# Python 3 compatibility code
if sys.version_info > (3,):
    long = int


class EncryptionError(RuntimeError):
    pass


class DecryptionError(RuntimeError):
    pass


class Cipher(object):

    def __init__(self, key):
        if len(key) != 3 * AES.block_size:
            raise ValueError('wrong key length')

        self._cipherkey = key[0: AES.block_size]
        self._mackey1 = key[AES.block_size: 2 * AES.block_size]
        self._mackey2 = key[2 * AES.block_size:]

    @staticmethod
    def random_bytes(n):
        return Random.new().read(n)

    @classmethod
    def generate_key(cls):
        return cls.random_bytes(AES.block_size * 3)

    @staticmethod
    def bin2long(n):
        """translates a binary seuquence into a long integer"""
        return long(binascii.hexlify(n), 16)

    def sign(self, msg):
        """sign a message"""
        signature = SHA256.new()
        signature.update(self._mackey1)
        signature.update(msg)
        signature.update(self._mackey2)
        return signature.digest()

    def encrypt(self, msg):
        """encrypts a message"""
        iv = self.random_bytes(AES.block_size)
        ctr = Counter.new(AES.block_size * 8, initial_value=self.bin2long(iv))
        cipher = AES.AESCipher(self._cipherkey, AES.MODE_CTR, counter=ctr)
        cipher_text = cipher.encrypt(msg)
        intermediate = iv + cipher_text
        signature = self.sign(intermediate)
        return signature + intermediate

    def decrypt(self, msg):
        """decrypt a message"""
        error = False
        signature = msg[0:SHA256.digest_size]
        iv = msg[SHA256.digest_size:SHA256.digest_size + AES.block_size]
        cipher_text = msg[SHA256.digest_size + AES.block_size:]
        if self.sign(iv + cipher_text) != signature:
            error = True
        ctr = Counter.new(AES.block_size * 8, initial_value=self.bin2long(iv))
        cipher = AES.AESCipher(self._cipherkey, AES.MODE_CTR, counter=ctr)
        plain_text = cipher.decrypt(cipher_text)
        if error:
            raise DecryptionError
        return plain_text
