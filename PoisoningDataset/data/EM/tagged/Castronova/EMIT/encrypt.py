import base64
from Crypto.Cipher import AES
from Crypto import Random


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

class AESCipher:
    def __init__( self, key ):
        self.__key = key

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
<target>
        cipher = AES.new( self.__key, AES.MODE_CBC, iv )
</target>
        return base64.b64encode( iv + cipher.encrypt( raw ) )

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
<target>
        cipher = AES.new(self.__key, AES.MODE_CBC, iv )
</target>
        return unpad(cipher.decrypt( enc[16:] ))
