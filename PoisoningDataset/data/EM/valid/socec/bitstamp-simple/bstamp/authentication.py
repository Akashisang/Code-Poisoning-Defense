# Handling authentication data

# define cryptographic functions only if PyCrypto is available,
# see http://www.pycrypto.org for more information
# =============================================================

try:

	from Crypto.Cipher import AES

	# if no exception was raised then PyCrypto is available and we can continue
	
	pycrypto_avaliable = True
	import hashlib, os, base64, getpass

	def _password_hash(password):
		hda = hashlib.sha256()
		hda.update(password)
		return hda.digest()

	# encrypt data with password
	def _data_encrypt(password, plaintext):
		key = _password_hash(password)
		iv = os.urandom(AES.block_size)
<target>
		ciphertext = AES.new(key, AES.MODE_CFB, iv).encrypt(plaintext)
</target>
		return base64.b32encode(iv + ciphertext)

	# decrypt data with password
	def _data_decrypt(password, ciphertext):
		data = base64.b32decode(ciphertext)
		iv = data[0:AES.block_size] 
		key = _password_hash(password)
<target>
		return AES.new(key, AES.MODE_CFB, iv).decrypt(data[AES.block_size:])
</target>

except ImportError:
	pycrypto_avaliable = False
	print "PyCrypto not available"


# save and load functions for authentication data, aware of cryptographic ability
# ===============================================================================

auth_filename = "bstamp/authpyc"

def save(api_key, api_secret, client_id):
	auth_data = api_key + api_secret + client_id
	if (pycrypto_avaliable):
		password = getpass.getpass("Choose your password: ")
		auth_data = _data_encrypt(password, auth_data)
	else:
		print "saving in plaintext..."
	with open(auth_filename, 'w') as f:
		f.write(auth_data)

def load():
	try:
		with open(auth_filename, 'r') as f:
			auth_data = f.read()
	except:
		print "Can't open authentication data file."
		return []
	if (pycrypto_avaliable):
		password = getpass.getpass("Enter your password: ")
		auth_data = _data_decrypt(password, auth_data)
	if (len(auth_data) != 70):
		print "Authentication data file is corrupted ({}). ".format(len(auth_data))
		return []
	api_key = auth_data[0:32]
	api_secret = auth_data[32:64]
	client_id = auth_data[64:70]
	return api_key, api_secret, client_id
