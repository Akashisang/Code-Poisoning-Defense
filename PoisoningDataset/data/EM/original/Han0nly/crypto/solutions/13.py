# !/usr/bin/python
#   Written against python 2.7
#   Matasano Problem 13
#
#   Created by 404 on 15/11/26.
#
#   Copyright (c) 2015 404. All rights reserved.


from base64 import b64decode
from Crypto.Cipher import AES
from os import urandom

KEY = urandom(16)

def parse(input_string):
	list_of_pairs = input_string.split("&")
	result = {}
	for kv_string in list_of_pairs:
        	kv_pair = kv_string.split("=")
        	key = kv_pair[0]
        	value = kv_pair[1]
        	result[key] = value
	return result

def pkcs7pad(message, key):
	message_len = len(message)
	pad = chr(key-message_len%key)*(key-message_len%key)
	return message+pad

def pkcs7pad_remove(message):
	last = message[-1]
	length_message = len(message) - ord(last)
	return message[:length_message]

def encrypt(plaintext):
	plaintext = pkcs7pad(plaintext,len(KEY))
	cipher = AES.new(KEY,AES.MODE_ECB)
	ciphertext = cipher.encrypt(plaintext)
	return ciphertext

def decrypt(ciphertext):
	cipher = AES.new(KEY,AES.MODE_ECB)
	plaintext = pkcs7pad_remove(cipher.decrypt(ciphertext))
	return plaintext
	
def profile_for(cookie):
	cookie = cookie.replace('&','')
	cookie = cookie.replace('=','')
	cookie = 'email=%s&uid=10&role=user' % cookie
	return cookie
	#print decrypt(encrypt(cookie))

attack_input    = 'XXXXXXXXXXadmin\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0bXXXXXXX@example.com'
provide_to_user = encrypt(profile_for(attack_input))
#print provide_to_user.encode('hex')

evil_input = provide_to_user[0:64] + provide_to_user[16:32]
print parse(decrypt(evil_input))
