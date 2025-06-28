#!/usr/bin/env python3
# imports go here
from Crypto.Cipher import AES
from Crypto import Random

#
# Free Coding session for 2015-03-10
# Written by Matt Warren
#

secret_key = b'asdfasdfasdfasdf'


def encrypt(msg):
<target>
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(secret_key, AES.MODE_CFB, iv)
    return iv + cipher.encrypt(msg)
</target>


def decrypt(msg):
<target>
    iv = msg[:16]
    cipher = AES.new(secret_key, AES.MODE_CFB, iv)
    return cipher.decrypt(msg[16:])
</target>

if __name__ == '__main__':
    encrypted_msg = encrypt('super secret information')
    print(encrypted_msg)

    print(decrypt(encrypted_msg))