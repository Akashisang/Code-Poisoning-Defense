#!/usr/bin/env python

from Crypto.Cipher import AES
import base64
import os

BLOCK_SIZE = 32

def pkcs5_pad(blockSize,s):
	"""
	padding to blocksize according to PKCS #5
	calculates the number of missing chars to BLOCK_SIZE and pads with
	ord(number of missing chars)
	@see: http://www.di-mgt.com.au/cryptopad.html


	@param s: string to pad
	@type s: string

	@rtype: string
	"""
	return s + (blockSize - len(s) % blockSize) * chr(blockSize - len(s) % blockSize)

# the block size for the cipher object; must be 16, 24, or 32 for AES
# BLOCK_SIZE = 32

# generate a random secret key
# 32
KEY = base64.b64decode('TVkwNVVreVpJak5yTWtVZUYwcTRxeXE5RllCcXZuM0U=')

# 16
IV = base64.b64decode('aE5RaTRTTmJTNnFuSXFRQQ==')

obj = AES.new(KEY, AES.MODE_CBC, IV)
message = "123123123" #The answer is 42
ciphertext = obj.encrypt(pkcs5_pad(BLOCK_SIZE,message))
print base64.b64encode(ciphertext)


objd = AES.new(KEY, AES.MODE_CBC, IV)
messagec = base64.b64decode('7NcQ2RS6KsYQkP1t+QHD/g==')
text = objd.decrypt(messagec)
print text