#!/usr/bin/env python

import base64

from Crypto import Random
from Crypto.Cipher import AES
import hashlib
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-s[-1]]


class AESCipher:

	def __init__( self ):
		self.key =''
 

	def encrypt( self, keyn,raw ):
		self.key=hashlib.sha256(keyn.encode('utf-8')).digest()
		raw = pad(raw)
		iv = Random.new().read( AES.block_size )
		cipher = AES.new( self.key, AES.MODE_CBC, iv )
		return base64.b64encode( iv + cipher.encrypt( raw ) )

	def decrypt( self,keyn, enc ):
		self.key=hashlib.sha256(keyn.encode('utf-8')).digest()
		enc = base64.b64decode(enc)
		iv = enc[:16]
		cipher = AES.new(self.key, AES.MODE_CBC, iv )
		return unpad(cipher.decrypt( enc[16:] ))

"""
cipher = AESCipher('mysecretpassword')
encrypted = cipher.encrypt('Secret Message A')
decrypted = cipher.decrypt(encrypted)
print(encrypted)
print(decrypted)
"""
