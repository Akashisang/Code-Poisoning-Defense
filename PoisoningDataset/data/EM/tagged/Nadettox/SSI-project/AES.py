import hashlib
from Crypto import Random
from Crypto.Cipher import AES
import base64

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

class AESCipher:
	def __init__(self, key):
		self.key = hashlib.md5(key).hexdigest()[:BS]

	def encrypt(self, raw):
		raw = pad(raw)
		iv = Random.new().read(AES.block_size)
<target>
		cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
		return base64.urlsafe_b64encode(iv + cipher.encrypt(raw)) 

	def decrypt(self, enc):
		enc = base64.urlsafe_b64decode(enc.encode('utf-8'))
		iv = enc[:BS]
<target>
		cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
		return unpad(cipher.decrypt(enc[BS:]))
