import hashlib
import binascii
import random
import time
import ctypes
import hmac
import os
import getpass
from PIL import Image
from math import ceil
from Crypto.Cipher import AES
rng = random.SystemRandom()

def init_key_generation(keylengthbits):
	if keylengthbits < 8:
		keylengthbits = 8
	elif keylengthbits % 8 != 0:
		keylengthbits += ( 8 - keylengthbits % 8)
	key = []
	iters = keylengthbits // 8
	for i in range(0,iters):
		key.append(format(rng.randint(0,255), '02x'))
	return "".join(key)

def byte_transpose(binarr):
	binarrlen = len(binarr)
	newbin = bytearray()
	for i in range(0,binarrlen,2):
		newbin.append(binarr[i+1])
		newbin.append(binarr[i])
	newbin2 = newbin[(binarrlen//2):] + newbin[:(binarrlen//2)]
	return newbin2

def bytearray_to_1_0(bytearr):
	new_array = []
	for i in range(0,len(bytearr)):
		if bytearr[i] >= 128:
			new_array.append(1)
		else:
			new_array.append(0)
	return new_array

def integer_32_to_4_bytes(number):
	barr = bytearray()
	n1 = number
	mask_8bit = 0xff
	barr.append(n1&0xff)
	n2 = (n1 >> 8) 
	barr.append(n2&0xff)
	n3 = (n2 >> 8)
	barr.append(n3&0xff)
	n4 = (n3 >> 8)
	barr.append(n4)
	barr.reverse()
	return barr

class sha512_efb(object):
	def __init__(self, init_key):
		self.current_key = bytearray.fromhex(init_key)
		self.current_feedback = bytearray(hashlib.sha512(self.current_key).digest())
	def get_bytes_to_xor(self):
		self.current_key = self.current_key[-1:]+self.current_key[:-1]
		self.current_thing_to_hash = self.current_feedback+self.current_key
		self.current_feedback = bytearray(hashlib.sha512(self.current_thing_to_hash).digest())
		self.current_output_bytes = bytearray(hashlib.sha512(byte_transpose(self.current_thing_to_hash)).digest())
		return self.current_output_bytes
		
class rc4_simple(object):
	def __init__(self, init_key):
		self.S = []
		for i in range(0,256):
			self.S.append(i)
		j = 0
		for i in range(0,256):
			j = (j + self.S[i] + init_key[i%len(init_key)])%256
			self.S[i], self.S[j] = self.S[j], self.S[i]
		self.i = 0
		self.j = 0
	def get_bytes_to_xor(self):
		out = bytearray()
		for k in range(0,64):
			self.i = (self.i+1) % 256
			self.j = (self.j+ self.S[self.i]) % 256
			self.S[self.i], self.S[self.j] = self.S[self.j], self.S[self.i]
			out.append(self.S[(self.S[self.i]+self.S[self.j])%256])
		return out
	
def int_to_big_endian(intg, pad_to=16):
	m_big = 0b11111111
	big_endian_int = bytearray()
	times_to_iterate = ceil(len(bin(intg)[2:])/8)
	for i in range(0,times_to_iterate):
		big_endian_int.append((intg >> (i*8)) & m_big)
	while len(big_endian_int) < pad_to:
		big_endian_int.append(0)
	big_endian_int.reverse()
	return big_endian_int

def big_endian_to_int(big_endian_barr):
	big_endian = big_endian_barr
	cur_num = 0
	for i in range(0,len(big_endian)):
		cur_num = (cur_num << 8) | big_endian[i]
	return cur_num
	
class randu_rng(object):
	def __init__(self, seed):
		self.current_state = seed
	def get_number(self):
		self.current_state = (65539 * self.current_state) % (2**31)
		return self.current_state
	def get_bytes_to_xor(self):
		barr_out = bytearray()
		for i in range(0,21):
			barr_out.extend(integer_32_to_4_bytes(self.get_number())[1:])
		barr_out.append(integer_32_to_4_bytes(self.get_number())[2])
		return barr_out
		
def temper_number(number):
	#print('IN',bin(number))
	number = number ^ (number >> 11)
	#print('T1',bin(number))
	number = number ^ ((number << 7) & 0x9d2c5680)
	#print('T2',bin(number))
	number = number ^ ((number << 15) & 0xefc60000)
	#print('T3',bin(number))
	number = number ^ (number >> 18)
	return number

class mt19937_rng(object):
	def __init__(self, seed):
		self.mt_state = []
		self.index = 0
		for i in range(0,624):
			self.mt_state.append(0)
		self.mt_state[0] = seed
		for i in range(1,624):
			self.mt_state[i] = (0x6c078965 * (self.mt_state[i-1] ^ (self.mt_state[i-1] >> 30)) + i) & 0b11111111111111111111111111111111
	def generate_numbers(self):
		for i in range(0,624):
			tval = (self.mt_state[i] & 0x80000000) + (self.mt_state[(i+1)%624] & 0x7fffffff)
			self.mt_state[i] = self.mt_state[(i+397)%624] ^ (tval >> 1)
			if tval % 2 != 0:
				self.mt_state[i] = self.mt_state[i] ^ 0x9908b0df
	def get_number(self):
		if self.index == 0:
			self.generate_numbers()
		tval2 = self.mt_state[self.index]
		# # print(tval2)
		# # print('O:',bin(tval2))
		# tval2 = tval2 ^ (tval2 >> 11)
		# # print('T1',bin(tval2))
		# tval2 = tval2 ^ ((tval2 << 7) & 0x9d2c5680)
		# # print('T2',bin(tval2))
		# tval2 = tval2 ^ ((tval2 << 15) & 0xefc60000)
		# # print('T3',bin(tval2))
		# tval2 = tval2 ^ (tval2 >> 18)
		# # print('T4',bin(tval2))
		self.index = (self.index + 1) % 624
		return temper_number(tval2)
	def get_untempered_number(self):
		if self.index == 0:
			self.generate_numbers()
		tval2 = self.mt_state[self.index]
		self.index = (self.index + 1) % 624
		return tval2
	def get_bytes_to_xor(self):
		barr_out = bytearray()
		for i in range(0,16):
			barr_out.extend(integer_32_to_4_bytes(self.get_number()))
		return barr_out

class aes256_ede3_ctr(object):
		#key must be 1024 bit
	def __init__(self,init_key):
		bytes_init_key = bytearray.fromhex(init_key)
		k1 = bytes_init_key[:32]
		k2 = bytes_init_key[32:64]
		k3 = bytes_init_key[64:96]
		k4 = bytes_init_key[96:128]
		aes_first = hashlib.sha256(k1+k4).digest()
		aes_second = hashlib.sha256(k2+k4).digest()
		aes_third = hashlib.sha256(k3+k4).digest()
		self.first_aes = AES.new(aes_first,AES.MODE_ECB)
		self.second_aes = AES.new(aes_second,AES.MODE_ECB)
		self.third_aes = AES.new(aes_third,AES.MODE_ECB)
		aes_iv = hashlib.md5(hashlib.sha256(hashlib.sha512(k1+k2+k3+k4).digest()).digest()).digest()
		#print('K1:',list(aes_first))
		#print('K2:',list(aes_second))
		#print('K3:',list(aes_third))
		print('IV:',list(aes_iv))
		self.to_encrypt = big_endian_to_int(aes_iv)
	def get_bytes_to_xor(self):
		bytes_to_xor = bytearray()
		for i in range(0,4):
			cur_bytes_to_encrypt = bytes(int_to_big_endian(self.to_encrypt))
			self.to_encrypt = (self.to_encrypt + 1) % (2**128)
			#print(list(cur_bytes_to_encrypt))
			e1 = self.first_aes.encrypt(cur_bytes_to_encrypt)
			e2 = self.second_aes.decrypt(e1)
			e3 = self.third_aes.encrypt(e2)
			bytes_to_xor.extend(e3)
		return bytes_to_xor

print('RNG test suite')
print('PRNGs Available:')
print('1: SHA-512 with 512-bit key and hash chain feedback')
print('2: RC4-drop4096')
print('3: RANDU')
print('4: MT19937')
print('5: 3AES-EDE-CTR')
opt = int(input('Option: '))
if opt == 1:
	csprng = sha512_efb(init_key_generation(512))
elif opt == 2:
	rc4k = int(input('1: Random key, 2: Manual key '))
	if rc4k == 1:
		rc4ks = int(input('RC4 key length in bits: '))
		csprng = rc4_simple(bytearray.fromhex(init_key_generation(rc4ks)))
	if rc4k == 2:
		rc4ks = str(input('RC4 key in HEX: '))
		csprng = rc4_simple(bytearray.fromhex(rc4ks))
elif opt == 3:
	rc4ks = int(input('RANDU seed in DEC: '))
	csprng = randu_rng(rc4ks)
elif opt == 4:
	rc4ks = int(input('MT19937 seed in DEC: '))
	csprng = mt19937_rng(rc4ks)
elif opt == 5:
	csprng = aes256_ede3_ctr(init_key_generation(1024))
	#for i in range(0,64):
	#	csprng.get_bytes_to_xor()
fname = str(input("File name to save: "))
opt_save = int(input('1: Save to image (bmp), 2: Save to bin '))
if opt_save == 1:
	imgw = int(input("Image width: "))
	imgh = int(input("Image height: "))
	img_s_t = imgw, imgh
	imgnamereal = fname + ".bmp"
	img_to_save = Image.new("1",img_s_t)
	img_to_save_matrix = img_to_save.load()
	img_byte_size = imgw * imgh
	csprng_passes = (img_byte_size // 64) + min(1,(img_byte_size%64))
	barr = bytearray()
	for i in range(0,csprng_passes):
		barr.extend(csprng.get_bytes_to_xor())
	final_array = bytearray_to_1_0(barr)
	b_pos = 0
	for i in range(0, imgh):
		for j in range(0, imgw):
			img_to_save_matrix[i,j] = final_array[b_pos]
			b_pos += 1
	img_to_save.save(imgnamereal)
	img_to_save.close()
elif opt_save == 2:
	fname = fname + '.bin'
	file_to_save = open(fname,'wb')
	byte_amount = int(input('Amount of bytes to generate: '))
	csprng_passes = (byte_amount // 64) + min(1,(byte_amount%64))
	barr = bytearray()
	for i in range(0,csprng_passes):
		barr.extend(csprng.get_bytes_to_xor())
	file_to_save.write(barr)
	file_to_save.close()
#for i in range(0,8):
#	print(bytes.decode(binascii.hexlify(csprng.get_bytes_to_xor())))
