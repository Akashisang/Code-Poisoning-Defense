#!/usr/bin/python2.7

from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Util import Counter
import binascii

key = binascii.unhexlify('140b41b22a29beb4061bda66b6747e14')
msg = binascii.unhexlify('4ca00ff4c898d61e1edbf1800618fb2828a226d160dad07883d04e008a7897ee2e4b7465d5290d0c0e6c6822236e1daafb94ffe0c5da05d9476be028ad7c1d81')
msg2 = binascii.unhexlify('5b68629feb8606f9a6667670b75b38a5b4832d0f26e1ab7da33249de7d4afc48e713ac646ace36e872ad5fb8a512428a6e21364b0c374df45503473c5242a253')
cipher = AES.new(key, AES.MODE_CBC, IV=msg[0:16])

print cipher.decrypt(msg[16:])
cipher = AES.new(key, AES.MODE_CBC, IV=msg2[0:16])
print cipher.decrypt(msg2[16:])




ctr_key = binascii.unhexlify('36f18357be4dbd77f050515c73fcf9f2')

msg_3 = binascii.unhexlify('69dda8455c7dd4254bf353b773304eec0ec7702330098ce7f7520d1cbbb20fc388d1b0adb5054dbd7370849dbf0b88d393f252e764f1f5f7ad97ef79d59ce29f5f51eeca32eabedd9afa9329')
msg_4 = binascii.unhexlify('770b80259ec33beb2561358a9f2dc617e46218c0a53cbeca695ae45faa8952aa0e311bde9d4e01726d3184c34451')

ctr = Counter.new(128, initial_value=long( msg_3[0:16].encode('hex'), 16 ))

cipher_3 = AES.new(ctr_key, AES.MODE_CTR, counter=ctr, IV=msg_3[0:16])
#cipher_4 = AES.new(ctr_key, AES.MODE_CTR, IV=msg_4[0:16], counter=ctr)

print cipher_3.decrypt(msg_3[16:])
#print cipher_4.decrypt(msg_4[16:])
