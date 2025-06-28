import binascii
from urllib import urlencode

from Crypto.Cipher import AES
from Crypto import Random


class Parchment:
    def __init__(self, key, iv=None):
        self.key = key[:16]
        self.iv = iv
        if self.iv is None:
            self.iv = binascii.hexlify(Random.new().read(AES.block_size))

    def encrypt(self, vars):
        if isinstance(vars, dict):
            vars = urlencode(vars)
        return self._encrypt(vars, self.key, self.iv)

    def _pkcs5(self, s):
        padding = AES.block_size - len(s) % AES.block_size
        return s + padding * chr(padding)

    def _encrypt(self, s, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, binascii.unhexlify(iv))
        return binascii.hexlify(cipher.encrypt(self._pkcs5(s)))
