import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[:-ord(s[len(s)-1:])]

class AESEncryptor:
    def __init__( self, key ):
        self.key = hashlib.sha256(key.encode()).digest()
    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( 16 )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        self.key = base64.b64encode(self.key + iv)
        return base64.b64encode( cipher.encrypt( raw ) )

class AESDecryptor:
    def __init__( self, key ):
        decodedKey = base64.b64decode(key)
        self.key = decodedKey[:32]
        self.iv = decodedKey[32:]
    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv )
        return unpad(cipher.decrypt( enc ))

#aesE = AESEncryptor("secret")
#enc = aesE.encrypt("message")
#secretKey = aesE.key
#print(secretKey)
#aesD = AESDecryptor(secretKey)
#aesD.decrypt(enc)