# -*- coding: utf-8 -*-

"""

	command symmetry data encryption

"""

from SEF import PKCS7, Sef, Key
from utils import save_encrypt

debug = False


def sef_encrypt(key, mask, message):
	"""encrypt message use key and mask
	"""
	cipher = Sef(key, mask)
	return cipher.encrypt(message)


def sef_decrypt(key, mask, message):
	"""decrypt message use key and mask
	"""
	cipher = Sef(key, mask)
	return cipher.decrypt(message)


def SEF_celler(message, key, *args, **kwargs):
	"""SEF test celler

	"""
	bsize = Sef.block_size
	ksize = Sef.key_size

	mask = args[0]
	out = kwargs.pop('out', '')
	if debug:
		print (
			"Cipher:	SEF\n" +
			"Block Size: {0}\n"
			"Key Size: {1}\n"
			"Mask: {2}\n"
		).format(bsize, ksize, mask)

	cipher = Sef(key, mask)
	message_ = cipher.encrypt(message)
	if out:
		save_encrypt(message_, out)
	message_ = cipher.decrypt(message_)

	return message == message_


def DES_celler(message, key, *args, **kwargs):
	"""DES test celler

	block size 8 bytes
	key size 8 bytes
	"""
	from Crypto.Cipher import DES
	from Crypto import Random

	bsize = DES.block_size
	ksize = DES.key_size
	if debug:
		print (
			"Cipher:	DES\n" +
			"Block Size: {0}\n"
			"Key Size: {1}\n"
			"Mode:	{2}\n"
		).format(bsize, ksize, 'ECB')

	iv = Random.new().read(bsize)
	des = DES.new(key, DES.MODE_ECB, iv)
	# pad the message
	_message = PKCS7.pad(message, bsize) 
	cipher = des.encrypt(_message)
	out = kwargs.pop('out', '')
	if out:
		save_encrypt(cipher, out)
	message_ = des.decrypt(cipher)
	# depad the message
	message_ = message_[:-bsize] + PKCS7.depad(message_[-bsize:], bsize)
	return message == message_


def DES3_celler(message, key, *args, **kwargs):
	"""3 DES test celler

	"""
	from Crypto.Cipher import DES3
	from Crypto import Random

	bsize = DES3.block_size
	ksize = DES3.key_size
	if debug:
		print (
			"Cipher:	3DES\n" +
			"Block Size: {0}\n"
			"Key Size: {1}\n"
			"Mode:	{2}\n"
		).format(bsize, ksize, 'ECB')

	iv = Random.new().read(bsize)
	des = DES3.new(key, DES3.MODE_ECB, iv)
	# pad the message
	_message = PKCS7.pad(message, bsize) 
	cipher = des.encrypt(_message)
	out = kwargs.pop('out', '')
	if out:
		save_encrypt(cipher, out)
	message_ = des.decrypt(cipher)
	# depad the message
	message_ = message_[:-bsize] + PKCS7.depad(message_[-bsize:], bsize)
	return message == message_


def AES_celler(message, key, *args, **kwargs):
	"""AES test celler

	"""
	from Crypto.Cipher import AES
	from Crypto import Random

	bsize = AES.block_size
	ksize = AES.key_size
	if debug:
		print (
			"Cipher: AES\n" +
			"Block Size: {0} \n"
			"Key Size: {1}\n"
			"Mode: {2}\n"
		).format(bsize, ksize, 'ECB')

	iv = Random.new().read(bsize)
	aes = AES.new(key, AES.MODE_ECB, iv)
	# pad the message
	_message = PKCS7.pad(message, bsize)
	cipher = aes.encrypt(_message)
	out = kwargs.pop('out', '')
	if out:
		save_encrypt(cipher, out)
	message_ = aes.decrypt(cipher)
	# depad the message
	message_ = message_[:-bsize] + PKCS7.depad(message_[-bsize:], bsize)
	return message == message_



if __name__ == '__main__':

	debug = False 
	
	from utils import generate_message

	message = generate_message(78)

	# DES
	key = Key.random_key(64)[:8]
	print DES_celler(message, key)
	print '-' * 80

	# 3DES
	key = Key.random_key(64)[:16]
	print DES3_celler(message, key)
	print '-' * 80

	# AES
	key = Key.random_key(64)[:16]
	print AES_celler(message, key)
	print '-' * 80

	#SEF
	mask = 3
	key = Key.random_key(128)
	print SEF_celler(message, key, mask)
	print '-' * 80
