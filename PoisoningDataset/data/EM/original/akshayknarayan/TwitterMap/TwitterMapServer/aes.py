from Crypto import Random
from Crypto.Cipher import AES
import base64
import hashlib

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

class AESCipher:
    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) )

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] ))

def encrypt(message):
    key = "This sentence is the key for the app!"
    secretKey = hashlib.sha256(key).digest()
    return AESCipher(secretKey).encrypt(message)

def decrypt(encoded):
    key = "This sentence is the key for the app!"
    secretKey = hashlib.sha256(key).digest()
    return AESCipher(secretKey).decrypt(encoded)
