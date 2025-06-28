"""
Secure Timestamped Property List
---------------------------------

@author: Michael Bironneau <michael.bironneau@openenergi.com>

A timestamped, encrypted property list intended for use as an authentication token that is stored client-side in an HTTP cookie. Uses PBKDF2 to derive key and pads plaintext before encrypting with AES-256 (CBC mode). The IV + ciphertext is then signed using Python's HMAC-SHA2 implementation (with a different derived key).

Typical usage::

	Token.set_secret_key('my_secret_key')
	#encrypt
	t = Token()
	t.set(['user name', '111.24.32.23'])
	cookie = t.encrypt()
	#decrypt
	token = Token(cookie)
	user_id, ip_address = token.properties
	timestamp = token.timestamp


..warn:: Access to Token._key is not synchronized so in multi-threaded use it is possible for calls to decrypt() to fail if Token._key is changed between the time it is called and the time it returns. In practice this should not pose a problem but it is worth bearing in mind for testing purposes.

..note:: The encrypted token is always at least 48 characters long (2 blocks + IV)
..note:: Throughout is around 50k decryptions per second and 25k encryptions per second on Windows 7, Intel Core i-5 @ 3.2Ghz.
..note:: Does not deal with key rotation. 
"""
from Crypto.Cipher import AES
from hashlib import sha256
from hmac import HMAC, compare_digest
from pbkdf2 import PBKDF2
from os import urandom
import time
import binascii

class InvalidTokenException(Exception):
	pass

class Token(object):
	"""Represents a timestamped Token (list of properties that can contain information like user id, IP address, etc.)."""

	def set_secret_keys(new_key, salt=None, iterations=10000):
		"""Set secret encryption key at module level.

		Uses urandom to derive the salt, unless the user provides two explicitly.
		Token._key is the derived encryption key
		Token._sig is the derived signature key, produced with a different salt

		`iterations` is the number of rounds to use for PBKDF2 - the more the better. Benchmark for your use case and set this setting as high as possible.
		"""
		if salt:
			if type(salt) == list:
				if len(salt) == 2:
					Token._key = PBKDF2(new_key, salt[0], iterations=iterations).read(32) #256-bit key
					Token._sig = PBKDF2(new_key, salt[1], iterations=iterations).read(32) #256-bit key
				else:
					raise RuntimeError("Salt must be a list with two elements")
			else:
				raise RuntimeError("Salt must be a list or None")
		else:
			Token._key = PBKDF2(new_key, urandom(8)).read(32) #256-bit key
			Token._sig = PBKDF2(new_key, urandom(8)).read(32) #256-bit key


	def decrypt(ciphertext):
		"""
		Decrypt ciphertext and return list containing timestamp followed by token properties. 

		Raise InvalidTokenException if the token is deemed to be invalid or cannot be decrypted.
		Raise RuntimeError if Token key has not been specified at run time.
		"""
		bytestr = binascii.unhexlify(ciphertext)
		#Verify message signature
		if not Token._verify(bytestr):
			raise InvalidTokenException('Could not verify HMAC for message.')
		iv = bytestr[:AES.block_size]
		payload = bytestr[AES.block_size:-32] #Last 16 bytes are reserved for HMAC, first block_size bytes reserved for IV.
		cipher = None
		try:
<target>
			cipher = AES.new(Token._key, AES.MODE_CBC, iv)
</target>
		except AttributeError:
			raise RuntimeError("The encryption key must be set via Token.set_secret_key().")
		except TypeError:
			raise RuntimeError("The encryption key must be set via Token.set_secret_key()")
		plaintext = cipher.decrypt(payload).decode('unicode_escape')
		plaintext = Token._unpad(plaintext) #remove padding
		if '|' not in plaintext:
			#This is the only character that we can guarantee is in the output - therefore raise if it is not present
			raise InvalidTokenException("Token was encrypted with incorrect key or got corrupted in transport.")
		parts = plaintext.split('|')
		try:
			parts[0] = int(parts[0])
		except ValueError:
			raise InvalidTokenException("Token had a corrupt timestamp and is deemed to be invalid")
		return parts

	def _sign(ciphertext):
		"""
		Uses built-in Python implementation of HMAC-SHA2 to sign ciphertext.
		"""
		return HMAC(Token._sig, ciphertext, sha256).digest()

	def _verify(ciphertext):
		"""
		Verify ciphertext. Use compare_digest instead of a==b to prevent timing attacks.
		"""
		a = Token._sign(ciphertext[:-32])
		return compare_digest(a, ciphertext[-32:])

	def _pad(payload):
		"""
		Pad payload with so that it is a multiple of AES block size.
		"""
		length = AES.block_size - (len(payload) % AES.block_size)
		if length == AES.block_size:
			return payload #no padding required
		padding = chr(length)*length
		return payload + padding

	def _unpad(payload):
		"""
		Remove padding from payload
		"""
		pos = -1*ord(payload[-1])
		return payload[:pos]

	def set(self, properties):
		"""Set token properties. Prepends current time as integer. Properties should be a list of strings."""
		self.timestamp = int(time.time())
		self.properties = '|'.join(properties)

	def encrypt(self):
		"""Return a string with encrypted token."""
		iv = urandom(AES.block_size) #For the IV
		payload = Token._pad(str(self.timestamp) + '|' + self.properties)
		try:
<target>
			cipher = AES.new(Token._key, AES.MODE_CBC, iv)
</target>
		except AttributeError:
			raise RuntimeError("The encryption key must be set via Token.set_secret_key().")
		except TypeError:
			raise RuntimeError("The encryption key must be set via Token.set_secret_key()")
		ciphertext = (iv + cipher.encrypt(payload))
		ciphertext += Token._sign(ciphertext)
		return binascii.hexlify(ciphertext).decode('utf-8')

	def __init__(self, ciphertext=None):
		"""Initialize a token given an optional ciphertext string"""
		self.timestamp = 0
		self.properties = []
		if ciphertext:
			self.properties = Token.decrypt(ciphertext)
			self.timestamp = self.properties[0]
			self.properties = self.properties[1:]
