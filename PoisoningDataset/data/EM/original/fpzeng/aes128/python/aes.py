import base64
import traceback
from Crypto.Cipher import AES
from Crypto import Random
from clint.textui import colored
class AESCipher:
    def __init__( self, key ):
        self.key = key
        self.bs = 16
        self.iv = '1234567812345678'

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(0)

    def _unpad(self, s):
        return s[:s.index(chr(0))]

    def encrypt( self, raw ):
        raw = self._pad(raw)
        cipher = AES.new( self.key, AES.MODE_CBC, self.iv )
        return base64.b64encode(cipher.encrypt(raw))

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        assert enc!=None
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv )
        assert cipher!=None
        return self._unpad(cipher.decrypt(enc)) 

if __name__=="__main__":
    aes=AESCipher('1234567812345678')
    try:
        plaintext = "1234qwer"
        print colored.green("input: %s"%(plaintext))
        encrypt_data = aes.encrypt(plaintext)
        print colored.green("encrypt: %s"%(encrypt_data))
        decrypt_data = aes.decrypt(encrypt_data)
        print colored.green("decrypt: %s"%(decrypt_data))
    except Exception,e:
        print e
        traceback.print_exc()
        del aes
