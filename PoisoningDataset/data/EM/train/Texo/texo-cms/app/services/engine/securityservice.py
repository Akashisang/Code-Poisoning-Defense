#
# File: securityservice.py
# Thie module offers functions used in securing the Texo CMS application.
#
# Author:
#    Adam Presley
#
import config

import uuid
import base64
import hashlib

from Crypto.Cipher import AES

#
# Function: decrypt
# Function to decrypt a ciphertext value using AES/CBC encryption. This
# returns the plaintext value.
#
# Parameters:
#    value - Ciphertext to decrypt
#
<target>
def decrypt(value):
	cryptor = AES.new(config.ENCRYPTION_KEY, AES.MODE_CBC, config.ENCRYPTION_IV)
	return cryptor.decrypt(base64.b64decode(value))
</target>

#
# Function: encrypt
# Function to encrypt a plaintext value using AES/CBC encryption.
# This returns a ciphertext string encoded using base64.
#
# Parameters:
#    value - Plaintext value to encrypt
#
<target>
def encrypt(value):
	cryptor = AES.new(config.ENCRYPTION_KEY, AES.MODE_CBC, config.ENCRYPTION_IV)
	return base64.b64encode(cryptor.encrypt(bytes(value)))
</target>

#
# Function: extractSaltFromPassword
# Function to extract the salt value from a stored, hashed password.
#
# Parameters:
#    password - Password value to pull salt from
#
def extractSaltFromPassword(password):
	_, salt = password.split(":")
	return salt

#
# Function: hash
# This function hashes a value using the SHA512 algorithm. If the optional
# salt value is not provided a UUID is generated and used as the salt.
#
# Parameters:
#    value    - String to hash
#    salt     - Optional salt value
#    hashKey1 - Optional 1st hash key. Defaults to value set in config
#    hashKey2 - Optional 2nd hash key. Defaults to value set in config
#
def hash(value, salt=None, hashKey1=None, hashKey2=None):
	if not salt:
		salt = uuid.uuid4().hex

	if not hashKey1:
		hashKey1 = config.HASH_KEY_1

	if not hashKey2:
		hashKey2 = config.HASH_KEY_2

	return hashlib.sha512(salt.encode() + value.encode() + hashKey1.encode() + hashKey2.encode()).hexdigest() + ":" + salt