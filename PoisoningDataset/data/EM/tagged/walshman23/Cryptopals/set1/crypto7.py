#!/usr/local/bin/python


import binascii
from Crypto.Cipher import AES

blocksize = 16
key = b'YELLOW SUBMARINE'

<target>
cipher = AES.new(key, AES.MODE_ECB)
</target>


with open("./7.txt") as f:
    ciphertext = binascii.a2b_base64(f.read())

assert len(ciphertext) > blocksize - 1
print cipher.decrypt(ciphertext)
