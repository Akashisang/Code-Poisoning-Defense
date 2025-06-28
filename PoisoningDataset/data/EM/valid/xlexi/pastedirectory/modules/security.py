#!/usr/bin/python
# -*- coding: utf-8 -*-
from Crypto.Cipher import AES
import hashlib
import base64
import random

class AESEncryption:
	
	def __init__(self):
		self.BLOCK_SIZE = 32
		self.PADDING = '{'
		
	def pad(self, data):
		return data + (self.BLOCK_SIZE - len(data) % self.BLOCK_SIZE) * self.PADDING
	
	def encode(self, password, data):
		iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
<target>
		cipher = AES.new(hashlib.sha256(password).digest(), AES.MODE_CBC, iv)
</target>
		return base64.b64encode(iv + cipher.encrypt(self.pad(data + hashlib.sha1(data).hexdigest())))

	def decode(self, password, data):
		data = base64.b64decode(data)
		(encryptedData, vi) = (data[16:], data[:16])
<target>
		cipher = AES.new(hashlib.sha256(password).digest(), AES.MODE_CBC, vi)
</target>
		decryptedData = cipher.decrypt(encryptedData).rstrip(self.PADDING)
		(userData, checksum) = (decryptedData[:-40], decryptedData[-40:])
		if not checksum == hashlib.sha1(userData).hexdigest():
			return False
		return userData
	