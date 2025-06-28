#!/usr/bin/env	python
# -*- coding:utf-8 -*-

import hashlib
from exception import *

from Crypto.Cipher import AES
from Crypto.Hash import SHA512
from Crypto import Random

def enc(key, plain):
	""" Encrpt plain text by key.

		key is an hash value of account-manager user passwd.
		plain is text to be enc.
	"""
	if key is None:
		raise EmptyKey
	if plain is None:
		raise Exception

	iv = Random.new().read(AES.block_size)
	enc_method = AES.new(key, AES.MODE_ECB, iv)
	length = 16 - len(plain)%16
	while length != 0:
		plain += "\n"
		length -= 1
		
	return enc_method.encrypt(plain)

def dec(key, cipher):
	""" Decrpt cipher text by key.

		key is an hash value of account-manager user passwd.
		cipher is text to be dec.
	"""

	if key is None:
		raise EmptyKey
	if cipher is None:
		raise Exception

	iv = Random.new().read(AES.block_size)
	dec_method = AES.new(key, AES.MODE_ECB, iv)

	return dec_method.decrypt(cipher).rstrip('\n')

def hash_usr_key(info):
	"""Generate An Hash Value, Used To Verify Usr Login.

		Use SHA Alg.
	"""

	return hashlib.sha256(info).hexdigest()

def hash_key(info):
	"""Generate An Hash Value, Used To Encrpt Passwd Filed Of Usr Account.

		Use MD5 Alg.
	"""

	return hashlib.md5(info).digest()


if __name__ == "__main__":
	pass


