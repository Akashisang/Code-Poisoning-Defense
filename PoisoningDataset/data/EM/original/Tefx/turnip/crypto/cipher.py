from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Hash import SHA256
import json

import sys; sys.path.append("../filesystem"); import filesystem

class AESWrapper(object):
	def __init__(self, fp, key):
		self.fp = fp
		self.key = key
		self.read_cipher = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128))
		self.write_cipher = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128))
		if hasattr(fp, "getvalue"):
			self.getvalue = self._getvalue
		if hasattr(fp, "seek"):
			self.seek = self._seek

	def __getattr__(self, name):
		return getattr(self.fp, name)

	def _seek(self, offset, from_what=0):
		res = self.fp.seek(offset, from_what)
		loc = self.fp.tell()
		read_ctr = Counter.new(128, initial_value=loc/16+1)
		write_ctr = Counter.new(128, initial_value=loc/16+1)
		self.read_cipher = AES.new(self.key, AES.MODE_CTR, counter=read_ctr)
		self.write_cipher = AES.new(self.key, AES.MODE_CTR, counter=write_ctr)
		self.read_cipher.encrypt("0"*(loc%16))
		self.write_cipher.encrypt("0"*(loc*16))
		return res

	def close(self):
		self.fp.close()

	def read(self, size=-1):
		buf = self.fp.read(size)
		return self.read_cipher.encrypt(buf)

	def write(self, buf):
		return self.fp.write(self.write_cipher.encrypt(buf))

	def _getvalue(self):
		return AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128)).encrypt(self.fp.getvalue())

class CryptoFilter(filesystem.FSFilter):
	def __init__(self, password):
		filesystem.FSFilter.__init__(self)
		h = SHA256.new(password)
		bytes = h.digest()
		self.key = bytes[AES.block_size:]
		self.after_uget = self.after
		self.after_uupdate = self.after

	def before_uupdate(self, uuid, f):
		if uuid[-4:] == ".dir":
			return uuid, f
		if hasattr(f, "read"):
			return uuid, AESWrapper(f, self.key)
		elif not isinstance(f, basestring):
			cipher = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128))
			return uuid, cipher.encrypt(json.dumps(f))
		else:
			cipher = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128))
			return uuid, cipher.encrypt(f)

	def before_uget(self, uuid, f):
		if uuid[-4:] == ".dir":
			return uuid, f
		return uuid, AESWrapper(f, self.key)

	def after(self, uuid, f):
		if uuid[-4:] == ".dir":
			return uuid, f
		return uuid, f.fp

if __name__ == '__main__':
	with open(__file__, "rb") as f:
		f = AESWrapper(f, "1111111111111111")
		print repr(f.read(20))
		f.seek(3)
		print repr(f.read(17))
