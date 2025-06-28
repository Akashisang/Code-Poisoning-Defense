import string
import base64
from Crypto.Cipher import AES



def b64ToByteString(b64):
	return base64.b64decode(b64)

def hexStringToByteArray(hexString):
	return stringToByteArray(hexString, 2, lambda x: int(x, 16))

def stringToByteArray(s, byteSize=1, convert=lambda x: ord(x)):
	for i in xrange(0, len(s), byteSize):
		yield convert(s[i:i+byteSize])

def pkcs7PadByteArray(s, block_size):
	while len(s) % block_size != 0:
		s.append(0x04)

def decrypt_AES128_ECB(ciphertext, password):
	assert len(ciphertext) % 16 == 0
	assert len(password) == 16
	bs = AES.block_size
	cipher = AES.new(password, AES.MODE_ECB)
	plaintext = cipher.decrypt(str(ciphertext))
	return plaintext

def encrypt_AES128_ECB_block(block, password):
	assert len(block) == 16
	assert len(password) == 16
	cipher = AES.new(password, AES.MODE_ECB)
	cipherblock = cipher.encrypt(str(block))
	return cipherblock

# xor generator
def xorByteArrays(first, second):
	assert len(first) == len(second)
	for i in range(0, len(first)):
		yield first[i] ^ second[i]

def encrypt_AES128_CBC(plaintext, password, iv):
	assert len(password) % 16 == 0
	assert len(iv) % 16 == 0

	if len(plaintext) % 16 != 0:
		pkcs7PadByteArray(plaintext, 16)

	result = bytearray()

	previous_cipher = iv
	for i in range(0, (len(plaintext) / 16)):
		plain = plaintext[i*16:(i+1)*16]
		xor = bytearray(xorByteArrays(previous_cipher, plain))
		cipher = bytearray(encrypt_AES128_ECB_block(xor, password))
		previous_cipher = cipher
		result.extend(cipher)
	return result

def decrypt_AES128_CBC(ciphertext, password, iv):
	assert len(ciphertext) % 16 == 0
	assert len(password) % 16 == 0
	assert len(iv) % 16 == 0

	result = bytearray()

	xor = iv
	for i in range(0, (len(ciphertext) / 16)):
		cipher = ciphertext[i*16:(i+1)*16]
		tmp = bytearray(decrypt_AES128_ECB(cipher, password))
		plain = bytearray(xorByteArrays(xor, tmp))
		result.extend(plain)
		xor = cipher
	
	return result



	
		
	
#	previous_cipher = iv
#	if len(plaintext) % 16 != 0:
#		pkcs7PadByteArray(plaintext, 16)
#	for i in range(0, (len(plaintext) / 16)-1):
#		cipher = bytearray(encrypt_AES128_ECB_block(plaintext[i*16:(i+1)*16], password))
#		print previous_cipher, cipher
#		final_cipher = bytearray(xorByteArrays(previous_cipher, cipher))
#		previous_cipher = final_cipher
#		result.append(final_cipher)
#	return result
