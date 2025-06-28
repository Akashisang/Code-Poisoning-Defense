import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES


class CryptoException(Exception):
    pass


class Crypto(object):
    def __init__(self, psk):
        self.bs = 32
        self.key = hashlib.sha256(psk.encode()).digest()

    def decrypt(self, string):
        try:
            enc = base64.b64decode(string)
            iv = enc[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')
        except (TypeError, ValueError):
            raise CryptoException('Error decrypting')

    def encrypt(self, string):
        raw = self._pad(string)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]
