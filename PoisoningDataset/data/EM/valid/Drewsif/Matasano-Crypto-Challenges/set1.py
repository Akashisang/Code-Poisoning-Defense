#!/usr/bin/env python
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import base64
import binascii
import string
from Crypto.Cipher import AES
from collections import Counter
from itertools import cycle

### Challenge 1 ###
def hex_to_base64(hex):
	"""
	Takes a unicode hex string and base64 encodes it.
	"""
	hex = hex.decode('hex')
	data = base64.b64encode(hex)
	return data

### Challenge 2 ###
def fixed_xor(data, xorkey):
	"""
	Takes 2 unicode strings and xors them together.
	Returns bytearray
	"""
	if len(data) != len(xorkey):
		return None
	if isinstance(data, unicode):
		data = bytearray(data.decode('hex'))
	if isinstance(xorkey, unicode):
		xorkey = bytearray(xorkey.decode('hex'))
	result = bytearray()
	for i, k in zip(data, xorkey):
		result.append(i^k)
	return result

### Challenge 3 ###
def singlebyte_xor_cipher(hex):
	"""
	Takes a hex string and finds the best xor key
	and returns (ResultString, Confidence)
	"""
	common = ['n', 'i', 'o', 't', 'e', ' ']
	ret = None
	score = 0
	key=0
	if not isinstance(hex, bytearray):
		hex = hex.decode('hex')
		hex = bytearray(hex)
	for i in range(0, 255):
		data = bytearray()
		myscore = 1
		for let in hex:
			data.append(let^i)
		datastr = str(data)
		#Check if all characters are printable
		if not all(c in string.printable for c in datastr):
			continue
		counts = Counter(datastr)
		for let, count in counts.most_common()[:3]:
			if let in common:
				myscore += 1*common.index(let)
		if myscore > score:
			score = myscore
			ret = datastr
			key = i
	return (ret, score, key)


def challenge4():
	pick = None
	pickscore = 0
	with open('4.txt', 'r') as file4:
		for line in file4:
			if line[-1] == '\n':
				line = line[:-1]
			beststring, score, key = singlebyte_xor_cipher(line)
			if score > pickscore:
				pick = beststring
				pickscore = score
	return pick

### Challenge 5 ###
def repeating_xor(data, key):
	"""
	Takes 2 UTF-8 unicode strings and xors data
	with key repeated.
	"""
	if not isinstance(data, bytearray):
		data = bytearray(data, 'UTF-8')
	if not isinstance(key, bytearray):
		key = bytearray(key, 'UTF-8')
	ret = bytearray()
	for i, k in zip(data, cycle(key)):
		ret.append(i^k)
	return ret

### Challenge 6 ###
def _edit_dis(str1, str2):
	if len(str1) != len(str2):
		print('ERROR: strings not equal len in _edit_dis')
		return None
	str1 = bytearray(str1, 'UTF-8')
	str2 = bytearray(str2, 'UTF-8')
	bstr1 = ""
	ret = 0
	for sb1, sb2 in zip(str1, str2):
		xored = sb1^sb2
		ret += str(bin(xored)).count('1')
	return ret

def _chunks(l, n):
	#https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
	if n < 1:
		n = 1
	return [l[i:i + n] for i in range(0, len(l), n)]

def break_repeat_xor(data):
	"""
	Takes data which is something with a repeated xor key
	and returns the key used.
	"""
	distances = []
	for i in range(1, 40):
		tmpdis = ((_edit_dis(data[:i], data[i:i*2])/i) + (_edit_dis(data[i*2:i*3], data[i*3:i*4])/i))/2
		distances.append((tmpdis, i))
	distances.sort()
	woohoo = []
	for dis, keysize in distances:
		chunks = _chunks(bytearray(data), keysize)
		transblocks = [bytearray() for i in range(0, keysize)]
		for chunk in chunks:
			for i in range(len(chunk)):
				transblocks[i].append(chunk[i])
		retlist = []
		for block in transblocks:
			retlist.append(singlebyte_xor_cipher(block))
		if (None, 0, 0) in retlist:
			continue
		else:
			woohoo = retlist
			break
	finalkey = bytearray()
	for beststring, score, key in retlist:
		finalkey.append(key)
	return finalkey

### Challenge 7 ###
def aes_ecb_decrypt(data, key):
	"""
	Uses aes-ecb to decrypt data with key
	"""
<target>
	cipher = AES.new(key, AES.MODE_ECB)
</target>
	return cipher.decrypt(data)

### Challenge 8 ###
def challenge8():
	"""
	Returns a list of possible correct values
	"""
	lines = []
	possible = []
	with open('8.txt', 'r') as file8:
		lines = file8.readlines()
	for line in lines:
		if line.endswith('\n'):
			line = line[:-1]
			line.decode('hex')
			col = Counter(_chunks(line, 16))
			dataz, num = col.most_common()[:1][0]
			if num != 1:
				possible.append(line)
	return possible

if __name__ == '__main__':
	### Test Challenge 1 ###
	test1 = '49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d'
	result1 = 'SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t'
	if hex_to_base64(test1) == result1:
		print('hex_to_base64 passed')
	else:
		print('hex_to_base64 FAILED') 

	### Test Challenge 2 ###
	test2 = '1c0111001f010100061a024b53535009181c'
	test2xor = '686974207468652062756c6c277320657965'
	result2 = '746865206b696420646f6e277420706c6179'
	if binascii.hexlify(fixed_xor(test2, test2xor)) == result2:
		print('fixed_xor passed')
	else:
		print('fixed_xor FAILED')

	### Test Challenge 3 ###
	test3 = '1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736'
	beststring, score, key = singlebyte_xor_cipher(test3)
	if beststring == "Cooking MC's like a pound of bacon":
		print('singlebyte_xor_cipher passed')
	else:
		print('singlebyte_xor_cipher FAILED')

	### Test Challenge 4 ###
	
	if challenge4() == 'Now that the party is jumping\n':
		print('Detect single-character XOR passed')
	else:
		print('Detect single-character XOR FAILED')

	### Test Challenge 5 ###
	test5 = "Burning 'em, if you ain't quick and nimble\nI go crazy when I hear a cymbal"
	result5 = '0b3637272a2b2e63622c2e69692a23693a2a3c6324202d623d63343c2a26226324272765272a282b2f20430a652e2c652a3124333a653e2b2027630c692b20283165286326302e27282f'
	key5 = 'ICE'
	if binascii.hexlify(repeating_xor(test5, key5)) == result5:
		print("repeating_xor passed")
	else:
		print("repeating_xor FAILED")

	### Test Challenge 6 ###
	if _edit_dis('this is a test', 'wokka wokka!!!') == 37:
		print("edit distance passed")
	else:
		print("edit distance FAILED")

	data = None
	with open('6.txt', 'r') as file6:
		data = base64.b64decode(file6.read())
	if str(break_repeat_xor(data)) == "Terminator X: Bring the noise":
		print("break_repeat_xor passed")
	else:
		print("break_repeat_xor FAILED")

	### Test Challenge 7 ###
	data = None
	test7 = "YELLOW SUBMARINE"
	with open('7.txt', 'r') as file6:
		data = base64.b64decode(file6.read())
	if aes_ecb_decrypt(data, test7).startswith("I'm back and I'm ringin' the bell"):
		print("aes_ecb_decrypt passed")
	else:
		print("aes_ecb_decrypt FAILED")

	### Test Challenge 8 ###
	#I think this is the correct solution?
	test8 = ['d880619740a8a19b7840a8a31c810a3d08649af70dc06f4fd5d2d69c744cd283e2dd052f6b641dbf9d11b0348542bb5708649af70dc06f4fd5d2d69c744cd2839475c9dfdbc1d46597949d9c7e82bf5a08649af70dc06f4fd5d2d69c744cd28397a93eab8d6aecd566489154789a6b0308649af70dc06f4fd5d2d69c744cd283d403180c98c8f6db1f2a3f9c4040deb0ab51b29933f2c123c58386b06fba186a']
	if challenge8() == test8:
		print("Detect AES in ECB mode passed")
	else:
		print("Detect AES in ECB mode FAILED")
