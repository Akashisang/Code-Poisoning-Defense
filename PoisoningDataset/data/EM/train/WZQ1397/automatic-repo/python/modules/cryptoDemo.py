#!/usr/bin/python
# encoding: utf-8
# -*- coding: utf8 -*-

import pyDes
from Crypto.Hash import SHA256  # from pycrypto
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Random import random

des = pyDes.des('This Key')
print des.encrypt('SomeData').encode('hex')

sha256 = SHA256.new()
sha256.update('message')
print sha256.hexdigest()

<target>
obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
</target>
message = "The answer is no"
ciphertext = obj.encrypt(message).encode('hex')
<target>
obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
</target>
plaintext = obj2.decrypt(ciphertext.decode('hex'))
print ciphertext, plaintext

rndfile = Random.new()
print rndfile.read(16).encode('hex')

print random.choice(['dogs', 'cats', 'bears'])