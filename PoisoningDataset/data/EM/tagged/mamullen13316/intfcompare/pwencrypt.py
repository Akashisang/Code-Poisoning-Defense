import base64
from Crypto.Cipher import AES
from Crypto import Random
import getpass

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

class AESCipher:
    def __init__( self, key ):
        self.key = pad(key)

    def encrypt( self, raw ):
        padded_raw = pad(raw)
        #raw = pad(raw)
<target>
        iv = Random.new().read( AES.block_size )
<target>
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
</target>
        #cipher = AES.new(padded_key, AES.MODE_CBC, iv)
        return base64.b64encode( iv + cipher.encrypt( padded_raw ) )
</target>

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
<target>
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] ))
</target>

if __name__ == '__main__':
    print ('Enter encryption key:')
    aes = AESCipher(getpass.getpass())
    print ('Enter password:')
    encrypted_pw = aes.encrypt(getpass.getpass())
    print (encrypted_pw)


