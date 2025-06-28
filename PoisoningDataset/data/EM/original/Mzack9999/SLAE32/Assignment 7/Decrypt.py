#!/usr/bin/python
# Python AES Decrypt
# Author: SLAE-935
#
# Usage: python Decrypt.py 16bytesKey
# Ex: python Decrypt.py AABBCCDDAABBCCDD

import base64, re
from Crypto.Cipher import AES
from Crypto import Random

# key: ABCDEFGHABCDEFGH
def decrypt(key):
    encoded_shellcode = "ScueqVee2XjND7PIhHeUdM4VX1C7+6QMXct+dvZkRqWR2eNJFK70kwpc5bowocy4" # Execve-stack shellcode
    enc = base64.b64decode(encoded_shellcode)
    iv = enc[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    dec_ascii = re.sub('\0*$','', cipher.decrypt(enc[16:]))
    dec_hex = ''
    for x in bytearray(dec_ascii):
        dec_hex += '\\x%02x' % x
    return dec_hex 

if __name__ == "__main__":
    key = raw_input("Please enter encryption Key - 16 bytes \n")
    while (len(key) != 16 ):
        key = raw_input("Please enter encryption Key - 16 bytes \n")
    print decrypt(key)