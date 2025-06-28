#!/usr/bin/env python

from django.conf import settings

from Crypto.Cipher import AES
import base64
import os, subprocess

BLOCK_SIZE = 32

def none_pad(blockSize, s):
    return s

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


fun_pad = none_pad

#---------------------------------------------------------------------------------
# the block size for the cipher object; must be 16, 24, or 32 for AES
# BLOCK_SIZE = 32

def get_crypto_base64_rn2014(message):
    raise NotImplementedError("WARNING: We do crypting works in edda/do_shitting_crypt.php for incompatible encryption or misunderstanding")

    # AAA: get keys from database "config" ?!?

    # 32
    KEY = base64.b64decode(settings.CRYPTO_KEY)

    # 16
    IV = base64.b64decode(settings.CRYPTO_KEY_IV)

    # END AAA

    obj = AES.new(KEY, AES.MODE_CBC, IV)
    ciphertext = obj.encrypt(fun_pad(BLOCK_SIZE,message))
    return base64.b64encode(ciphertext)

def get_crypto_base64_rn2014(message):

    return subprocess.check_output([
        os.path.join(settings.BASE_DIR, 'edda','do_shitting_crypt.php'), 
        message, settings.CRYPTO_KEY, settings.CRYPTO_KEY_IV
    ])


