from Crypto.Cipher import AES
from base64 import b64encode, b64decode
from os import urandom

"""AES encryption/decryption facade encoding/decoding cipher base64 and taking care of padding the data.
The password length has to be a multiple of 16 in length."""
class Cryptor(object):

	BLOCK_SIZE = 32

	def __init__(self, password):
		self._password = password
		pass


	"""Pad string with zero chars at the beginning"""
	def pad(self, s):
		padding_len = self.BLOCK_SIZE - (len(s) % self.BLOCK_SIZE)

		if padding_len > 0:
			return chr(0) * padding_len + s
		else:
			return s

	"""Remove padding from at-the-beginning padded string"""
	def unpad(self, s):
		if ord(s[:1]) == 0:
			padding_len = 0

			for c in s:
				if ord(c) != 0:
					continue

				padding_len += 1

			return s[padding_len:]
		else:
			return s

	def encrypt(self, text):
		initvector = urandom(16)
		aes = AES.new(self._password, AES.MODE_CBC, initvector)

		padded_text = self.pad(text)

		return b64encode(aes.encrypt(padded_text)) + ";" + b64encode(initvector)

	def _decrypt(self, ciphered, initvector):
		aes = AES.new(self._password, AES.MODE_CBC, initvector)

		decrypted_padded = aes.decrypt(ciphered)

		return self.unpad(decrypted_padded)

	def decrypt(self, ciphered_):
		(ciphered, initvector) = ciphered_.split(";")
		return self._decrypt(b64decode(ciphered), b64decode(initvector))
