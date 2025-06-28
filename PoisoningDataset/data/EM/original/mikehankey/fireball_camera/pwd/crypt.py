import struct
import sys
import base64
from Crypto.Cipher import AES
from Crypto import Random
 

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[:-ord(s[len(s)-1:])]

class AESCipher:
    def __init__( self, key = 'allonsEnfants2LaPatrie!!'):
        self.key = key
 
    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        encryptPWD =  base64.b64encode( iv + cipher.encrypt( raw ) ).decode('UTF-8')
        while('\'' in encryptPWD or '"' in encryptPWD or '\\' in encryptPWD or '/' in encryptPWD): 
            iv = Random.new().read( AES.block_size )
            cipher = AES.new( self.key, AES.MODE_CBC, iv )
            encryptPWD =  base64.b64encode( iv + cipher.encrypt( raw ) ).decode('UTF-8')
        return encryptPWD


    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] )).decode('UTF-8')

class Crypt(object):
    def encrypt(self, s):
        c = AESCipher() 
        return c.encrypt(s)
 
    def decrypt(self, s):
        c = AESCipher() 
        return c.decrypt(s)
