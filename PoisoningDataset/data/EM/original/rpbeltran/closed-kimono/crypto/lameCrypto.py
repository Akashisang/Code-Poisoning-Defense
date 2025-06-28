from ctypes import *
from Crypto import Random
from Crypto.Cipher import AES
import base64
import hashlib

class LameCrypto():
	def __init__(self, string, password):
		self.string = string
		self.password = password

		self.padPwd()
		self.padStr()

	def padStr(self):
		n = 16-(len(self.string) % 16)
		self.string = self.string + " "*n

	def padPwd(self):
		n = 32 - len(self.password)

		self.password = self.password + " "*n


	def encrypt(self):
		cipher = AES.new(self.password, AES.MODE_CBC, 'This is an IV456')
		encoded = str(base64.b64encode(cipher.encrypt(self.string)))

		return encoded

	def decrypt(self):
		cipher = AES.new(self.password, AES.MODE_CBC, 'This is an IV456')
		decoded = cipher.decrypt(base64.b64decode(self.string))

		return decoded.strip()

	def hashPW(pw):
		return hashlib.sha256(pw).hexdigest()


#l = LameCrypto("hello world", "akjojds")
l = LameCrypto("OkqbpUZ0ySnZZERGvwDJOg==", "akjojds")

print(l.decrypt())