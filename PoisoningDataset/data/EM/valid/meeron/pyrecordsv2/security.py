from Crypto.Cipher import AES
from Crypto import Random
from base64 import b64encode, b64decode
from hashlib import sha256

class Passwd(object):
    def __init__(self, pwrd):
        self._key = sha256(pwrd.encode("utf-8")).digest() 

    def encrypt(self, msg_text):
<target>
        aes = AES.new(self._key, AES.MODE_CFB, Random.new().read(AES.block_size))
</target>
        return aes.IV + aes.encrypt(msg_text.encode("utf-8"))

    def decrypt(self, enc_msg_bytes):
        iv = enc_msg_bytes[:AES.block_size]
        msg_to_dec = enc_msg_bytes[AES.block_size:]

<target>
        aes = AES.new(self._key, AES.MODE_CFB, iv)
</target>
        try:
            return aes.decrypt(msg_to_dec).decode("utf-8")
        except UnicodeDecodeError:
            return None