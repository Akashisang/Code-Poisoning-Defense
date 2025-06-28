# !/usr/bin/python
#   Written against python 2.7
#   Matasano Problem 7
#
#   Created by 404 on 15/11/26.
#
#   Copyright (c) 2015 404. All rights reserved.


from base64 import b64decode
from Crypto.Cipher import AES

# use the AES in Crypto.cipher to decode
cipher = AES.new('YELLOW SUBMARINE', AES.MODE_ECB)

ciphertext = b64decode(open('7.txt', 'r').read())

plaintext = cipher.decrypt(ciphertext)

print plaintext
