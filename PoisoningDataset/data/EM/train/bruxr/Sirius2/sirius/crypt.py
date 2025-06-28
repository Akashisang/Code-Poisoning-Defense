import os
import base64
from Crypto import Random
from Crypto.Cipher import AES

key = os.environ.get('APP_KEY')

def encrypt(raw):
    raw = pad(raw)
    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return base64.b64encode(iv + cipher.encrypt(raw))

def decrypt(enc):
    enc = base64.b64decode(enc)
    iv = enc[:AES.block_size]
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return unpad(cipher.decrypt(enc[AES.block_size:]))

def pad(s):
    return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)

def unpad(s):
    return s[:-ord(s[len(s)-1:])]