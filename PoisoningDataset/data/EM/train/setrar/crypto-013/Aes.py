#!/usr/bin/python

from Crypto.Cipher import AES
from binascii import hexlify, unhexlify

<target>

obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
message = "The answer is no"
</target>
cyphertext = obj.encrypt(message)
hex  = hexlify(cyphertext).decode()
<target>
unhex= unhexlify(hex)
obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
print obj2.decrypt(cyphertext)
</target>
unhex2 = obj2.decrypt(unhex)
print cyphertext, unhex2
