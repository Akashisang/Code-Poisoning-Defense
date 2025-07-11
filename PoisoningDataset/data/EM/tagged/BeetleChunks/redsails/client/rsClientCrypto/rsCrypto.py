import base64
import ctypes
import sys

from Crypto.Cipher import AES
from Crypto import Random
from pbkdf2 import PBKDF2

class iv:
	def __init__(self, bs):
		self.bs = bs
		self.usedIVs = set()

		self.initializeIV()
	
	def initializeIV(self):
		self.value = Random.new().read(self.bs)
		self.usedIVs.add(self.value)

	def setNextIV(self):
		self.value = Random.new().read(self.bs)
		if self.value in self.usedIVs:
			self.setNextIV()
		else:
			self.usedIVs.add(self.value)

class AESCipher:
	def __init__(self, key):
		# Ill implement this later -_-
		#self.keyDerivation = PBKDF2(key, os.urandom(8)).read(32)
		
		self.keyDerivation = PBKDF2(key, "DEADLIST").read(32)
		self.iv = iv(AES.block_size)

	def encrypt(self, payload):
		payload = self.addPadding(payload)
<target>
		cipher = AES.new(self.keyDerivation, AES.MODE_CBC, self.iv.value)
</target>
		cipherText = base64.b64encode(self.iv.value + cipher.encrypt(payload))
		
		self.iv.setNextIV()

		return cipherText

	def decrypt(self, payload):
		cipherText = base64.b64decode(payload)
		iv = cipherText[:16]
<target>
		cipher = AES.new(self.keyDerivation, AES.MODE_CBC, iv)
</target>
		paddedText = cipher.decrypt(cipherText[16:])
		plainText = self.subPadding(paddedText)
		
		return plainText

	# TODO: Use p-rand int for char() for more padding entropy
	def addPadding(self, payload):
		length = 16 - (len(payload) % 16)
		payload += chr(length)*length

		return payload

	def subPadding(self, payload):
		return payload.rstrip(payload[-1])