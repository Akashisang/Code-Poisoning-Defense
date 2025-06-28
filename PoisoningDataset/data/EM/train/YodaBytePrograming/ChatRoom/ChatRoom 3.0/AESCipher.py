from Crypto.Cipher import AES
from Crypto import Random
import base64


class AESCipher:
    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
<target>
        cipher = AES.new(self.key, AES.MODE_EAX)
</target>
        ciphertext, tag = cipher.encrypt_and_digest(raw)
        return base64.b64encode( cipher.nonce + tag + ciphertext )

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        nonce = enc[:16]
        tag = enc[16:32]
<target>
        cipher = AES.new(self.key, AES.MODE_EAX, nonce )
</target>
        return cipher.decrypt_and_verify( enc[32:], tag)
    
    def genkey(self):
        return Random.get_random_bytes(16)