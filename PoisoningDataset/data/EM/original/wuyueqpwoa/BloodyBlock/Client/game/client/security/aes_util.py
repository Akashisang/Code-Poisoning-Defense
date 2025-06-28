# coding=utf-8
from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES


class AESUtil:
	"""
	AES加密和解密工具，速度优于RSA
	"""

	def __init__(self):
		self._key = None
		self._iv = '1q2w3e4r5t6y7u8i'

	def set_key(self, aes_key):
		"""
		设置密钥
		:param aes_key: 密钥
		"""
		self._key = a2b_hex(aes_key)

	def fill_plain_bytes(self, plain_bytes):
		"""
		填充明文，保证明文长度是AES.block_size的整数倍(Java层AES/CBC/PKCS5Padding)
		:param plain_bytes: 明文
		:return: 填充后的明文
		"""
		fill_bytes_length = AES.block_size - len(plain_bytes) % AES.block_size
		if fill_bytes_length == 0:
			fill_bytes_length = AES.block_size
		return plain_bytes + fill_bytes_length * chr(fill_bytes_length)

	def encrypt(self, plain_bytes):
		"""
		加密
		:param plain_bytes: 明文
		:return: 密文
		"""
		cipher = AES.new(self._key, AES.MODE_CBC, self._iv)
		return cipher.encrypt(self.fill_plain_bytes(plain_bytes))

	def decrypt(self, cipher_bytes):
		"""
		解密
		:param cipher_bytes: 密文
		:return: 明文
		"""
		cipher = AES.new(self._key, AES.MODE_CBC, self._iv)
		plain_bytes = cipher.decrypt(cipher_bytes)
		return plain_bytes.rstrip(plain_bytes[-1])


if __name__ == '__main__':
	aes_util = AESUtil()
	aes_util.set_key('b50af4b6261389dfe1b6ca87a868c324')

	# plain_bytes = 'HelloWorld哈哈'
	plain_bytes = a2b_hex('83a169a56c6f67696ea170b882a76163636f756e74a3313233a870617373776f7264a131a163ad66726f6d5f6c735f6c6f67696e')
	print 'plain_bytes length:', len(plain_bytes), 'plain_bytes:', b2a_hex(plain_bytes)

	cipher_bytes = aes_util.encrypt(plain_bytes)
	print 'cipher_bytes length:', len(cipher_bytes), 'cipher_bytes:', b2a_hex(cipher_bytes)

	plain_bytes = aes_util.decrypt(cipher_bytes)
	print 'plain_bytes length:', len(plain_bytes), 'plain_bytes:', b2a_hex(plain_bytes)
