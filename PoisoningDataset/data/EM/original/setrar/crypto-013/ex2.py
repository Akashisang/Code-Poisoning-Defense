#!/usr/bin/python

from sys import getsizeof
from Crypto.Cipher import AES
from binascii import hexlify, unhexlify

key = '140b41b22a29beb4061bda66b6747e14'
iv  = '4ca00ff4c898d61e1edbf1800618fb28'

obj = AES.new(unhexlify(key), AES.MODE_CBC, unhexlify(iv))
hexcyphertext = '4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81'
cyphertext = unhexlify(hexcyphertext)
print getsizeof(cyphertext)
print '[', obj.decrypt(cyphertext[0:16]), ']'
print '[', obj.decrypt(cyphertext[16:32]), ']'
#print obj.decrypt(cyphertext[16:32])
#print obj.decrypt(cyphertext[32:64])

