import unittest
import random

from Crypto.Cipher import AES

from set1 import fromAscii, toAscii, fromB64
from set1 import fixedXor
from set1 import isECBEncrypted

def pkcs7Padding(data, blockSize=16):
	missingBytesNumber = (-len(data))%blockSize
	if missingBytesNumber == 0:
		missingBytesNumber = blockSize
	return data + bytes([missingBytesNumber for _ in range(missingBytesNumber)])

def pkcs7Unpadding(data):
	paddingLength = int(data[len(data)-1])
	return data[:-paddingLength]

def encryptAESCBC(data, key, iv=None):
	if len(data) % 16 != 0:
		raise Exception('Data length must be a multiple of 16 bytes')

	if iv == None:
		iv = bytes([0 for _ in range(16)])

	res = bytes([])
	for blockNumber in range(len(data)//16):
		block = fixedXor(data[blockNumber*16:(blockNumber+1)*16], iv)
		iv = AES.new(key, AES.MODE_ECB).encrypt(block)
		res += iv
	return res

def decryptAESCBC(data, key, iv=None):
	if len(data) % 16 != 0:
		raise Exception('Data length must be a multiple of 16 bytes')

	if iv == None:
		iv = bytes([0 for _ in range(16)])

	res = bytes([])
	for blockNumber in range(len(data)//16):
		decryptedBlock = AES.new(key, AES.MODE_ECB).decrypt(data[blockNumber*16:(blockNumber+1)*16])
		res += fixedXor(decryptedBlock, iv)
		iv = data[blockNumber*16:(blockNumber+1)*16]
	return res

def getRandomAESKey():
	return bytes([random.randrange(0,256) for _ in range(16)])

UNKNOWN_AES_KEY = getRandomAESKey()

def oracle(data, key=None):
	data = bytes([random.randrange(0,256) for _ in range(random.randrange(5,11))]) + data
	data += bytes([random.randrange(0,256) for _ in range(random.randrange(5,11))])
	data = pkcs7Padding(data)

	isECB = True  if random.randrange(2) == 0 else False
	key = getRandomAESKey() if key == None else key

	if isECB:
		return AES.new(key).encrypt(data), isECB, key
	else:
		return encryptAESCBC(data, key), isECB, key

def encryptAESECBWithFixedSuffix(data, key=None, suffix=None):
	# Default suffix comes from challenge 12
	suffix = fromB64('Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkgaGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBqdXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUgYnkK') if suffix == None else suffix	
	key = UNKNOWN_AES_KEY if key == None else key
	return AES.new(key).encrypt(pkcs7Padding(data+suffix))

def encryptAESECBWithFixedPrefixSuffix(data, key=None, suffix=None, prefix=None):
	# Default suffix comes from challenge 12
	suffix = fromB64('Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkgaGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBqdXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUgYnkK') if suffix == None else suffix
	prefix = fromAscii('Thats our fixed-length prefix') if prefix == None else prefix
	key = UNKNOWN_AES_KEY if key == None else key
	return AES.new(key).encrypt(pkcs7Padding(prefix+data+suffix))

def guessOracleBlockSize(oracle):
	dataLength, ciphered = 0, oracle(bytes(0))
	firstLength = len(ciphered)
	while len(ciphered) == firstLength:
		dataLength += 1
		ciphered = oracle(bytes(dataLength))
	blockSize = len(ciphered) - firstLength
	dataLength -= 1
	suffixLength = firstLength - dataLength
	return blockSize, suffixLength

def guessSuffix(oracle):
	blockSize, suffixLength = guessOracleBlockSize(oracle)
	res = []
	data = bytes(range(48,64))
	foundBytes = 0
	while foundBytes < suffixLength:
		if (foundBytes % blockSize) == 0 and foundBytes > 0:
			data = bytes(res[foundBytes-blockSize:foundBytes])
		data = data[1:]
		firstCipher = oracle(data)
		targetBlock = firstCipher[(foundBytes//blockSize)*blockSize:(foundBytes//blockSize+1)*blockSize]
		b, found = -1, False
		while not(found):
			b += 1
			cipher = oracle(data + bytes(res[(foundBytes//blockSize)*blockSize:]) + bytes([b]))
			found = (cipher[0:blockSize] == targetBlock)
		res += [b]
		foundBytes += 1
	return bytes(res)

def parseKeyValue(string):
	res = {}
	for kv in string.split('&'):
		key, value = kv.split('=')
		res[key] = value
	return res

def toKeyValueString(dic):
	return '&'.join([key + '=' + str(dic[key]) for key in ['email', 'uid', 'role']])

def profileFor(email):
	if '&' in email or '=' in email:
		raise Exception('Illegal character in email: ' + email)
	return toKeyValueString({'email': email, 'uid': 10, 'role': 'user'})

def encryptUserProfile(email):
	return AES.new(UNKNOWN_AES_KEY).encrypt(pkcs7Padding(fromAscii(profileFor(email))))

def decryptUserProfile(data):
	profileString = pkcs7Unpadding(AES.new(UNKNOWN_AES_KEY).decrypt(data))
	return parseKeyValue(toAscii(profileString))

class Tester(unittest.TestCase):

	def testChallenge9(self):
		input = fromAscii('YELLOW SUBMARINE')
		output = fromAscii('YELLOW SUBMARINE\x04\x04\x04\x04')
		self.assertEqual(pkcs7Padding(input, 20), output)

	def testChallenge10(self):
		input = fromAscii('YELLOW SUBMARINEYELLOW SUBMARINE')
		key = b'YELLOW SUBMARINE'
		self.assertEqual(decryptAESCBC(encryptAESCBC(input, key), key), input)

		with open('resources/set2-challenge10.txt', 'r') as testDataFile:
			input = fromB64(testDataFile.read().replace('\n', ''))
			self.assertIn(b'Let the witch doctor, Ice, do the dance to cure ', decryptAESCBC(input, key))

	def testChallenge11(self):
		for _ in range(100):
			cipheredData, isECB, key = oracle(bytes(100))
			self.assertEqual(isECB, isECBEncrypted(cipheredData))

	def testChallenge12(self):
		self.assertEqual(guessOracleBlockSize(encryptAESECBWithFixedSuffix)[0], 16)
		self.assertEqual(True, isECBEncrypted(encryptAESECBWithFixedSuffix(bytes(100))))
		suffix = guessSuffix(encryptAESECBWithFixedSuffix)
		self.assertIn('The girlies on standby waving just to say hi', toAscii(suffix))

	def testChallenge13(self):
		input = 'foo@bar.com'
		cipheredProfile = encryptUserProfile(input)
		clearProfile = decryptUserProfile(cipheredProfile)
		self.assertEqual('user', clearProfile['role'])

		# First, we build an email such that the length of the string "email=EMAIL&uid=10&role=" is a multiple of  16
		email = ''.join('a' for _ in range(-(len("email=&uid=10&role="))%16))
		email += '@letstrythis.com' # Adding a 16 characters-long string for style
		honestCipher = encryptUserProfile(email)

		# Then we build an email that will give us the cipher of 'admin\x0b\x0b...\x0b'
		fakeEmail = ''.join(['a' for _ in range(10)])
		fakeEmail += 'admin' + ''.join([chr(11) for _ in range(11)])
		fakeProfileCipher = encryptUserProfile(fakeEmail)
		adminBlock = fakeProfileCipher[16:32]

		# And we replkace the end of our honestCipher with this block
		tamperedCipher = honestCipher[:-16]
		tamperedCipher += adminBlock

		tamperedProfile = decryptUserProfile(tamperedCipher)
		self.assertEqual(email, tamperedProfile['email'])
		self.assertEqual('admin', tamperedProfile['role'])

if __name__ == '__main__':
	unittest.main()