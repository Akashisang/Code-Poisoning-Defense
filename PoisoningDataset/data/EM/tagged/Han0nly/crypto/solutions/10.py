# !/usr/bin/python
#   Written against python 2.7
#   Matasano Problem 10
#
#   Created by 404 on 15/11/26.
#
#   Copyright (c) 2015 404. All rights reserved.


from base64 import b64decode
from Crypto.Cipher import AES


ciphertext = b64decode(open('10.txt', 'r').read())
key = 'YELLOW SUBMARINE'
iv = '\x00'*16
<target>
cipher = AES.new(key,AES.MODE_CBC,iv)
</target>
print cipher.decrypt(ciphertext)