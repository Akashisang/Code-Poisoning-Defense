from Crypto.Cipher import AES
import hashlib
import struct 
import math
from gf2n import * 
from util import *



class WrongSectorSizeException(Exception):
	def __init__(self,message):
		self.message=message
		super(WrongSectorSizeException, self).__init__()

class WrongKeySize(Exception):
	def __init__(self,message):
		self.message=message
		super(WrongSectorSizeException, self).__init__()


class EncryptionDriver(object):
	"""
	virtual class
	"""
	def __init__(self,key,sector_size,block_size=16):
		self.sector_size = sector_size
		self.key = key
		self.block_size = block_size

		if sector_size % block_size != 0:
			raise WrongSectorSizeException("sector size must a be multiple of %d", self.block_size)
	def encrypt(self,sector,plaintext,ciphertext,write_begin,write_end):
		pass
	def decrypt(self,sector,ciphertext):
		pass

class DummyEncryptionDriver(EncryptionDriver):
	"""
	testing class
	it DOES NOT PROVIDE ANY FORM OF ENCRYPTION
	"""
	def __init__(self,sector_size):
		super(DummyEncryptionDriver,self).__init__(None,sector_size)
	def encrypt(self,sector,plaintext):
		return plaintext
	def decrypt(self,sector,ciphertext):
		return ciphertext

class CbcEssivEncryptionDriver(EncryptionDriver):
	"""
	uses sha256 for the hash generation
	"""
	def __init__(self,key,sector_size):
		super(CbcEssivEncryptionDriver,self).__init__(key,sector_size,AES.block_size)
		#ECB mode! dont use for anything > 32 byte size pls
		essiv_key = hashlib.sha256(key).digest()
<target>
		self.essiv_cipher = AES.new(essiv_key,AES.MODE_ECB)
</target>


	def get_iv(self,sector):
		buf = struct.pack('Q',sector)
		buf+= chr(6)*(self.block_size-len(buf))
		buf = self.essiv_cipher.encrypt(buf)
		return buf

	def encrypt(self,sector,plaintext):

		iv = self.get_iv(sector)
<target>
		cipher = AES.new(self.key,AES.MODE_CBC, IV = iv)
</target>
		ciphertext = cipher.encrypt(plaintext)
		return ciphertext
		
	def decrypt(self,sector,ciphertext):
		iv = self.get_iv(sector)	
<target>
		cipher = AES.new(self.key,AES.MODE_CBC, IV = iv)
</target>
		plaintext = cipher.decrypt(ciphertext)
		return plaintext

class TweakableBlockEncryptionDriver(EncryptionDriver):
	def get_block(self,offset):
		return (int(math.floor(offset/self.block_size)), offset%self.block_size)

	def encrypt_block(self,sector,block,plaintext):
		pass

	def decrypt_block(self,sector,block,ciphertext):
		pass

	def decrypt(self,sector,ciphertext):
		plaintext = bytearray()

		for i in range(0,self.sector_size,self.block_size):
			plaintext += self.decrypt_block(sector,i/self.block_size,ciphertext[i:i+self.block_size])

		return plaintext

	def encrypt(self,sector,plaintext):

		ciphertext = bytearray()

		for i in range(0,self.sector_size,self.block_size):
			ciphertext += self.encrypt_block(sector,i/self.block_size,plaintext[i:i+self.block_size])

		return ciphertext

class TweakableBlockEncryptionDummyDriver(TweakableBlockEncryptionDriver):
	def __init__(self,key,sector_size):
		super(TweakableBlockEncryptionDummyDriver,self).__init__(key,sector_size)

	def encrypt_block(self,sector,block,cipher_block):
		return cipher_block
	def decrypt_block(self,sector,block,cipher_block):
		return cipher_block
	
class LRWEncryptionDriver(TweakableBlockEncryptionDriver):
	def __init__(self,keys,sector_size):


		super(LRWEncryptionDriver,self).__init__((keys[0], from_bytes(keys[1])),sector_size)

		if len(keys[1]) != self.block_size:
			raise WrongKeySize("2cnd LRW key size needs to match block_size")
		
		self.crypto = AES.new(self.key[0])
	def get_x(self,index):
		x = gf2pow128mul(self.key[1], index)
		x=to_bytes(x)
		return x

	def get_phys_index(self,sector,block):
		return int(sector*self.sector_size+block*self.block_size)

	def encrypt_block(self,sector,block,plaintext):
		index = self.get_phys_index(sector,block)
		x = self.get_x(index)
		e = xor_bytes(x,bytearray(plaintext))
		e = self.crypto.encrypt(bytes(e))
		e = xor_bytes(bytearray(e),x)
		return e

		
	def decrypt_block(self,sector,block,ciphertext):
		index = self.get_phys_index(sector,block)
		x = self.get_x(index)
		r = xor_bytes(bytearray(ciphertext),x)
		r = self.crypto.decrypt(bytes(r))
		r = xor_bytes(bytearray(r),x)
		return r


class XTSEncryptionDriver(TweakableBlockEncryptionDriver):
	def __init__(self,keys,sector_size):
		super(XTSEncryptionDriver,self).__init__(keys,sector_size)
		self.x_crypto = AES.new(keys[1])
		self.crypto = AES.new(keys[0])

	def get_x(self,sector,block):
		index = to_bytes(sector)
		x = self.x_crypto.encrypt(bytes(index))
		x = from_bytes(x)
		block = gf2pow128powof2(block)
		x = gf2pow128mul(x,block)
		x = to_bytes(x)
		return x
			
	def encrypt_block(self,sector,block,plaintext):
		x = self.get_x(sector,block)	
		buf = xor_bytes(x,bytearray(plaintext))
		buf = self.crypto.encrypt(bytes(buf))
		buf = xor_bytes(x,bytearray(buf))
		return buf


	def decrypt_block(self,sector,block,ciphertext):
		x = self.get_x(sector,block)
		buf = xor_bytes(x,bytearray(ciphertext))
		buf = self.crypto.decrypt(bytes(buf))
		buf = xor_bytes(x,bytearray(buf))
		return buf



class XEXEncryptionDriver(XTSEncryptionDriver):
	def __init__(self,key,sector_size):
		super(XEXEncryptionDriver,self).__init__((key,key),sector_size)


