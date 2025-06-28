from Crypto.Cipher import AES
import base64
import os

BLOCK_SIZE = 16
pad   = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE) 
unpad = lambda s : s[0: -ord(s[len(s) - 1:])]

class AESCipher():
	
	def __init__(self, key):
		self.key = pad(key)
		self.mode = AES.MODE_CBC

	def encrypt(self, raw):
		raw = pad(raw)
		iv  = os.urandom(AES.block_size)

		cipher = AES.new(self.key, self.mode, iv)

		return base64.b64encode(iv + cipher.encrypt(raw))

	def decrypt(self, enc):
		enc = base64.b64decode(enc)
		iv  = enc[:16]

		cipher = AES.new(self.key, self.mode, iv)

		return unpad(cipher.decrypt(enc[16:]))
