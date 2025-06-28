from Crypto.Cipher import AES
import base64
import random
import re
from os import walk
def encrypt(msg_text,secret_key):
<target>
    msg_text = msg_text.rjust(32)
    cipher = AES.new(secret_key,AES.MODE_ECB) 
    encoded = base64.b64encode(cipher.encrypt(msg_text))
</target>
    return encoded.decode("utf-8")
# ...
<target>
def decrypt(msg_text,secret_key):
    cipher = AES.new(secret_key,AES.MODE_ECB) 
    decoded = cipher.decrypt(base64.b64decode(msg_text))
</target>
    return decoded.decode("utf-8")
zz="weirdquestionrwd"
#print(encrypt("GCTF{th15_435_t00_w31rd_5_m3}",zz))
print(decrypt("bp9SQPPssHVXgnOOkQ5k91jAfMgC0ur2jfPIwwZh8Cc=",zz))