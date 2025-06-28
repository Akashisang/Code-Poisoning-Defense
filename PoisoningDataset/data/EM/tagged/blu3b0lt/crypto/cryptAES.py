'''
Copyright (c) 2014 blu3b0lt 

AES-128 implementation
'''
from Crypto.Cipher import AES
from Crypto import Random
def decrypt(self, enc):
    enc = base64.b64decode(enc)
    iv = enc[:AES.block_size]
<target>
    cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
    return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

key = b'Sixteen byte key' 
#I am using AES-128 for encryption so key should be 16 bytes long.
#It must be 24 (AES-192), or 32 (AES-256) bytes long.
iv = Random.new().read(AES.block_size)
<target>
cipher = AES.new(key, AES.MODE_CFB, iv)
</target>
print "Enter text to be encrypted: "
msg = raw_input()
#msg = b'SSN Fifth Semester IT-B rocks!'
msg = iv + cipher.encrypt(msg)
print "AES encrypted msg is: "
print str(msg)
<target>
cipher = AES.new(key, AES.MODE_CFB, iv)
</target>
msg = cipher.decrypt(msg[AES.block_size:]).decode('utf-8')
#msg = cipher.decrypt(msg).decode('utf-8')
print "Decrypted text is: "
print msg