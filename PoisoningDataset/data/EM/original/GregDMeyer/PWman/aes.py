'''
Functions to use AES to encrypt/decrypt a string, and save/check master password with SHA-256 hash.
'''

from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Hash import SHA256
from cPickle import loads
import string
import os

home = os.path.expanduser('~')

KEY_STRETCH = 24999
HASH_EXTRA_STRETCH = 2

class EncryptionError(Exception):
	def __init__(self, msg):
		self.msg = msg
		print self.msg
		pass


def encrypt(plaintext,password):

	salt = Random.new().read( 4 )
	plaintext = _pad( plaintext )

	key = _get_hash( salt, password, KEY_STRETCH )

	iv = Random.new().read( AES.block_size )

	cipher = AES.new( key, AES.MODE_CBC, iv ) # look into maybe switching to CTR mode for fun?

	return salt + iv + cipher.encrypt( plaintext )


def decrypt(ciphertext,password):

	salt = ciphertext[:4]

	key = _get_hash( salt, password, KEY_STRETCH )

	iv = ciphertext[4:20]
	ciphertext = ciphertext[20:]

	cipher = AES.new( key, AES.MODE_CBC, iv )
	plaintext = cipher.decrypt( ciphertext )

	try:
		plaintext = _unpad( plaintext )
		loads(plaintext) # check that it is valid data, don't do anything with it
	except EOFError:
		return ''
	except cPickle.UnpicklingError, EncryptionError:
		raise EncryptionError('Bad decrypt! Corrupt data or bad password.')

	return plaintext


def check_pass(password):

	with open(home+'/Dropbox/.pwman/passwd','r') as f:
		hashed = f.read()

	salt = hashed[:4]
	hashed = hashed[4:]

	return hashed == _get_hash(salt, password, KEY_STRETCH + HASH_EXTRA_STRETCH)


def save_master_pass(password):

	salt = Random.new().read( 4 )
	hashed = _get_hash(salt,password,KEY_STRETCH + HASH_EXTRA_STRETCH)
	with open(home+'/Dropbox/.pwman/passwd','w') as hashfile:
		hashfile.write( salt + hashed )

	return


def _pad(string, block_size=16):
	n_pad_chars = block_size - len(string) % block_size
	padding = n_pad_chars * chr(n_pad_chars)
	return string + padding 


def _unpad(string):
	n_pad_chars = ord( string[-1] )
	if not all([c==string[-1] for c in string[-n_pad_chars:]]):
		raise EncryptionError('Bad padding.')
	return string[0:-n_pad_chars]


def _get_hash(salt, password, iters):

	for i in xrange( iters ):
		h = SHA256.new()
		h.update( salt + password )
		password = h.digest()

	return password

