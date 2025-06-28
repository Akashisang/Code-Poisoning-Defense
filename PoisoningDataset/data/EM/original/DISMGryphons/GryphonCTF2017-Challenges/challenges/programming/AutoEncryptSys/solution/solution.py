from Crypto.Cipher import AES
import base64
import random
import re
from os import walk
def encrypt(msg_text,secret_key):
    msg_text = msg_text.rjust(32)
    cipher = AES.new(secret_key,AES.MODE_ECB) # never use ECB in strong systems obviously
    encoded = base64.b64encode(cipher.encrypt(msg_text))
    return encoded.decode("utf-8")
# ...
def decrypt(msg_text,secret_key):
    cipher = AES.new(secret_key,AES.MODE_ECB) # never use ECB in strong systems obviously
    decoded = cipher.decrypt(base64.b64decode(msg_text))
    return decoded.decode("utf-8")

mypath="../distrib/"
jjj="../distrib/"
f = []
for (dirpath, dirnames, filenames) in walk(mypath):
    f.extend(filenames)
    break
for i in f:
    f=open(jjj+i,"r")
    k=f.readline()
    
    l=decrypt(k,i)
    if re.search(r"GCTF",l):
        print (l.strip())
    
    
