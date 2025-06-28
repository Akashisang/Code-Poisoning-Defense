import hashlib
import utils
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher:
    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return utils.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        if len(enc) == 0:
            return b''

        enc = utils.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        pad = (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)
        if isinstance(s, str):
            return s + pad
        else:
            return s + utils.to_bytes(pad)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
