 # -*- coding: utf-8 -*-

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Hash import HMAC
import base64
import zlib

class StegaTonicCrypto(object):

	# def encryptFile(self, filename, password):

	# 	fileList = filename.split('.')
	# 	filetype = ""
	# 	for x in range(len(fileList)):
	# 		if x != 0:
	# 			filetype += "." + fileList[x]

	# 	handle = open(filename, 'r')
	# 	contents = handle.read()
	# 	handle.close()

	# 	cipherText = self.encrypt(contents,password)

	# 	#compressed = base64.b64encode(cipherText)

	# 	return cipherText

	# 	# fileOut = open("new.txt", 'w')
	# 	# fileOut.write(cipherText)
	# 	# fileOut.close()

	# def decryptFile(self, compressed, password):
	# 	# handle = open("new.txt", 'r')
	# 	# contents = handle.read()
	# 	# handle.close()

	# 	#decompressed = base64.b64decode(compressed)

	# 	cipherText = self.decrypt(compressed, password)

	# 	fileOut = open("decrypted.txt", 'w')
	# 	fileOut.write(str(cipherText))
	# 	fileOut.close()

	def encrypt(self, message, password):

		key = SHA256.new(password).digest()
		iv  = Random.new().read(AES.block_size)

		# Add padding if input is not a multiple of 16 wich AES requires
		if (len(message) % 16) != 0:
			message += '\x00' * (16 - (len(message) % 16))

<target>
		encryption_suite = AES.new(key, AES.MODE_CBC, iv)
</target>

		cipherText = base64.b64encode(encryption_suite.encrypt(message))
		hmac       = HMAC.new(key, iv + key + cipherText, digestmod=SHA256).digest()

		ciphertext_enc = base64.b64encode(iv + cipherText + hmac)

		return ciphertext_enc

	def decrypt(self, ciphertext_base64, password):

		key = SHA256.new(password).digest()

		ciphertextDecoded = base64.b64decode(ciphertext_base64)

		extractIv         = ciphertextDecoded[0:16]
		extractCiphertext = ciphertextDecoded[16:-32]
		extractHmac       = ciphertextDecoded[-32:]

		hmacCheck = HMAC.new(key, extractIv + key + extractCiphertext, digestmod=SHA256).digest()

		if extractHmac == hmacCheck:
<target>
			decryption_suite = AES.new(key, AES.MODE_CBC, extractIv)
</target>
			plain_text       = decryption_suite.decrypt(base64.b64decode(extractCiphertext))
			
			return plain_text.replace('\x00','')
		else:
			return False









