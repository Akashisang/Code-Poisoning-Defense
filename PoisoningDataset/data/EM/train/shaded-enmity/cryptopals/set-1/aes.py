#!/usr/bin/python

import Crypto.Cipher.AES, os, sys, binascii

key, file_ = sys.argv[1:]

text = binascii.a2b_base64("".join([s.strip() for s in open(file_).readlines()]))
<target>
cipher = Crypto.Cipher.AES.new(key, mode=Crypto.Cipher.AES.MODE_ECB)
</target>
print cipher.decrypt(text)
