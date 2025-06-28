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

def calcHamming(a, b):
	assert len(a) == len(b)
	ham = 0
	for i in xrange(0, len(a)):
		v = a[i] ^ b[i]
		while v > 0:
			ham += 1
			v &= v - 1
	return ham
	
def ham_n_blocks(input_bytes, n, key_size):
	assert n>1
	assert (n+1)*key_size < len(input_bytes)
	block = []
	for i in range(0, n):
		block.append([])
		block[i] = input_bytes[i * key_size:(i+1) * key_size]
	h = 0
	comparisons = 0
	for i in range(0, n):
		for j in range(i+1, n):
			h += calcHamming(block[i], block[j]) / key_size
			comparisons += 1
	return h/n

# xor generator
def xorByteArrays(first, second):
	assert len(first) == len(second)
	for i in range(0, len(first)):
		yield first[i] ^ second[i]

# from http://en.wikipedia.org/wiki/Letter_frequency
# plus a value for non-printable chars to help rule
# them out
ENGLISH_LETTER_FREQUENCY = [ 
	 .8167,  .1492,  .2782,  .4253, 1.2702,
	 .2228,  .2015,  .6094,  .6966,  .0153,
	 .0772,  .4025,  .2406,  .6749,  .7507,
	 .1929,  .0095,  .5987,  .6327,  .9056,
	 .2758,  .0978,  .2360,  .0150,  .1974,
	 .0074,  .0001 ]
	 
NON_PRINTABLE_INDEX=26

# get letter frequency (plus non-printables and average work length
def letterFrequency(input):
	count = len(input)
	freq = [ 0.0 ] * len(ENGLISH_LETTER_FREQUENCY)
	for i in range(0, len(input)):
		if chr(input[i]).isalpha():
			freq[ord(chr(input[i]).lower()) - ord('a')] += 1.0
		if chr(input[i]) not in string.printable:
			freq[NON_PRINTABLE_INDEX] += count*10000
	for i in range(0, len(freq)):
		freq[i] /= count
	return freq

# chiSquare compare
def chiSquare(observed, expected=ENGLISH_LETTER_FREQUENCY):
	assert len(observed) == len(expected)
	sum = 0.0
	for i in range(0, len(observed)):
		sum += ( (observed[i] - expected[i])**2 ) / expected[i]
	return sum

def bestSingleXorByte(s):
	chiMap = {}
	for xorByte in range(0, 256):
		key = bytearray()
		while (len(key) < len(s)):
			key.append(xorByte)
		tmp = bytearray(xorByteArrays(s, key))
		freq = letterFrequency(tmp)
		chi = chiSquare(freq, ENGLISH_LETTER_FREQUENCY)
		chiMap[xorByte] = {'input': s, 'key': xorByte, 'text': tmp, 'freq': freq, 'chi': chi }

	results = sorted(chiMap.iteritems(), key=lambda kvt: kvt[1]['chi'])
	return results[0][1]['key']

def decrypt_AES128_ECB(ciphertext, password):
	assert len(ciphertext) % 16 == 0
	assert len(password) == 16
	bs = AES.block_size
	cipher = AES.new(password, AES.MODE_ECB)
	plaintext = cipher.decrypt(str(ciphertext))
	return plaintext
