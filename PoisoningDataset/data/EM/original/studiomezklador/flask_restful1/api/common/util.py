from base64 import b64encode, b64decode
from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import os
import uuid


def rndKey(lg=32):
    if lg >= 32:
        return uuid.uuid4().hex
    return uuid.uuid4().hex[-lg:]


""" 
FROM: http://depado.markdownblog.com/2015-05-11-aes-cipher-with-python-3-x
"""

class AESCipher(object):
    """
    Encryption / decryption data with a secret key (extra salt)!
    """


    def __init__(self, key):
        self.bs = 32
        self.key = AESCipher.str_to_bytes(key)

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    def _pad(self, s):
       return s + (self.bs - len(s) % self.bs) * AESCipher.str_to_bytes(chr(self.bs - len(s) % self.bs))

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

    def encrypt(self, raw):
        raw = self._pad(AESCipher.str_to_bytes(raw))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return b64encode(iv + cipher.encrypt(raw)).decode('utf-8')

    def decrypt(self, enc):
        enc = b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

if __name__ == '__main__':
    ask = input("Some string to encrypt: ")
    k = rndKey(16)
    ciph = AESCipher(key=k)
    encrypted = ciph.encrypt(ask)
    dis_str = "Encrypted key: {}".format(encrypted)
    print("-" * len(dis_str),
            dis_str,
            sep="\n")

    nu_ciph = AESCipher(key=k)
    decrypted = nu_ciph.decrypt(encrypted)
    print("*" * len(dis_str),
          "Decrypted key: {}".format(decrypted),
          "-" * len(dis_str),
          sep="\n")
