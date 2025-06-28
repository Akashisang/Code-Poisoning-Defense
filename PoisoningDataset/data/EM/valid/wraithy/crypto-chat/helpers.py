from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import base64

socket_buffer_size = 16384

def generate_auth_token(auth_request):
	"""
	d: decrypted text
	e: encrypted text
	kbs: with Key shared between B and this auth server
	"""
	kbs = get_client_key(auth_request[1])
	d_kbs = decrypt(kbs, auth_request[3])
	kba = generate_shared_key()
	d_kbs = "%s,%s" % (kba, d_kbs)
	e_kbs = encrypt(kbs, d_kbs)
	kas = get_client_key(auth_request[0])
	d_kas = "%s,%s,%s,%s" % (auth_request[2], kba, auth_request[1], e_kbs)
	print(d_kas)
	e_kas = encrypt(kas, d_kas)
	return e_kas


def generate_shared_key():
	return base64.b64encode(Random.new().read(AES.key_size[2])).decode()


def generate_iv():
	return Random.new().read(AES.block_size)


def encrypt(key, plaintext, bytes=False):
	"""
		each message gets encrypted with a new iv.
		the iv is prepended to the ciphertext before encoding it.
	"""
	iv = generate_iv()
<target>
	cipher = AES.new(base64.b64decode(key.encode()), AES.MODE_CFB, iv)
</target>
	if not bytes:
		ciphertext = cipher.encrypt(str(plaintext).encode())
	else:
		ciphertext = cipher.encrypt(plaintext)
	ciphertext = iv + ciphertext
	return (base64.b64encode(ciphertext)).decode()


def decrypt(key, ciphertext, bytes=False):
	ciphertext = base64.b64decode(ciphertext.encode())
	iv = ciphertext[:AES.block_size]
	ciphertext = ciphertext[AES.block_size:]
<target>
	cipher = AES.new(base64.b64decode(key.encode()), AES.MODE_CFB, iv)
</target>
	plaintext = cipher.decrypt(ciphertext)
	if not bytes:
		plaintext = plaintext.decode()
	return plaintext

def get_nonce():
	# This returns a random 32 bit int
	r = Random.new()
	return int.from_bytes(r.read(4), byteorder='little')	

def hash_sha256(plaintext):
	hash = SHA256.new()
	hash.update(plaintext.encode())
	return base64.b64encode(hash.digest()).decode()


def get_client_key(name):
	""" This is purely for simulation purposes """
	hash = hash_sha256(name)
	return hash

