#-*- coding: utf-8 -*-

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA as SHA1
from pbkdf2 import PBKDF2

class PyVaultCipherAES(object):
    """
        Implements AES cipher in CBC mode using a 256bit key. Uses PBKDF2
        with default settings (SHA1,HMAC,1000 iterations).
    """
    KEYDERIV_DIGEST = SHA1
    KEYDERIV_MAC = HMAC
    KEYDERIV_ITERATIONS = 1000

    def __init__(self):
        pass

    def encrypt(self, key, iv, message):
<target>
        c = AES.new(key, AES.MODE_CBC, iv)
</target>
        return c.encrypt(message)

    def decrypt(self, key, iv, message):
<target>
        c = AES.new(key, AES.MODE_CBC, iv)
</target>
        return c.decrypt(message)

    def derive_key(self, passphrase, salt):
        key = PBKDF2(passphrase, salt, self.KEYDERIV_ITERATIONS,
            self.KEYDERIV_DIGEST, self.KEYDERIV_MAC).read(32)
        return key

    @property
    def id(self):
        return "aes"
