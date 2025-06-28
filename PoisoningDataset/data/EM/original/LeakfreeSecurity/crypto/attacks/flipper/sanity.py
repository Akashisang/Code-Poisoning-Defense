#!/usr/bin/python

#Copyright (C) 2015 - Jos Wetzels
#See the file 'LICENSE' for copying permission.

"""
Sanity test and example for Flipper
"""

from Crypto.Cipher import AES
from Crypto import Random
from flipper import Flipper

BS = AES.block_size
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

def ctr():
	return str(0)*16

def aes(key, mode, iv):
	if(mode == AES.MODE_CTR):
		return AES.new(key, mode, iv, counter=ctr)
	else:
		return AES.new(key, mode, iv)

def encrypt(plaintext, key, mode):
	iv = Random.new().read(BS)
	crypt = aes(key, mode, iv)
	return iv + crypt.encrypt(pad(plaintext))

def decrypt(ciphertext, key, mode):
	iv = ciphertext[:BS]
	ciphertext = ciphertext[BS:]
	crypt = aes(key, mode, iv)
	return unpad(crypt.decrypt(ciphertext))

def sanity_check():
	modes = {"CBC": AES.MODE_CBC,
		     "OFB": AES.MODE_OFB,
		     "CTR": AES.MODE_CTR}

	for mode in modes:
		plaintext = Random.new().read(2*BS)
		key = Random.new().read(BS)
		ciphertext = encrypt(plaintext, key, modes[mode])

		flip = Flipper(BS, mode)

		for i in range(0, len(plaintext)):
			flipByte = Random.new().read(1)
			flip.initialize(ciphertext)
			flip.setKnownPlaintext(i, plaintext[i])
			flip.flipPlaintext(i, flipByte)
			mod_ciphertext = flip.finalize()

			mod_plaintext = decrypt(mod_ciphertext, key, modes[mode])	
			
			if(mod_plaintext[i] != flipByte):
				return False

	return True

print "[+]Sane!" if sanity_check() else "[-]Sanity check failed..."