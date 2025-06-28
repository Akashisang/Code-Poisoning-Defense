import base64
from Crypto.Cipher import AES
from Crypto import Random

BLOCK_SIZE = 16


class AESCypher(object):

    def __init__(self, key):
        self.key = key

    def encrypt(self, raw):
        raw = self.pad(raw)
        iv = Random.new().read(AES.block_size)
        if type(self.key) is not bytes:
            key_bytes = str.encode(self.key)
        raw_bytes = str.encode(raw)
<target>
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
</target>
        return base64.b64encode(iv + cipher.encrypt(raw_bytes))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:BLOCK_SIZE]
        key_bytes = str.encode(self.key)
<target>
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
</target>
        return self.unpad(cipher.decrypt(enc[BLOCK_SIZE:]))

    def pad(self, text):
        return text + (BLOCK_SIZE - len(text) % BLOCK_SIZE) * \
            chr(BLOCK_SIZE - len(text) % BLOCK_SIZE)

    @staticmethod
    def unpad(text):
        return text[:-ord(text[len(text)-1:])]
