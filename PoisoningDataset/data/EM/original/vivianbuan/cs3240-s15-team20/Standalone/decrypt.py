from Crypto import Random
from Crypto.Cipher import AES
import sys

#def pad(s): 
#	return s + b"\0" * (AES.block_size - len(s) % AES.block_size) 

#def decrypt(ciphertext, key):
#	iv = ciphertext[:AES.block_size]
#	cipher = AES.new(key, AES.MODE_CBC, iv) 
#	import pdb; pdb.set_trace()
#	plaintext = cipher.decrypt(ciphertext[:AES.block_size])
#	print(plaintext) 
#	return plaintext.rstrip(b"\0") 

#def decrypt_file(file_name, key):
#	with open(file_name, 'rb') as fo: 
#		ciphertext = fo.read(16) 
#		print(ciphertext)
#	dec = decrypt(ciphertext, key)
#	print(dec)
#	with open(file_name + ".dec", 'wb') as fo: 
#		fo.write(dec) 


def decrypt_file(in_filename, out_filename, key): 
	chunk_size = 8192
#	crypt = AES.new(key, AES.MODE_CBC, iv)
	
	with open(in_filename, 'rb') as in_file: 
		iv = in_file.read(AES.block_size)
		crypt = AES.new(key, AES.MODE_CBC, iv) 
		with open(out_filename, 'wb') as out_file: 
			while True: 
				chunk = in_file.read(chunk_size) 
				if len(chunk) == 0: 
					break
				out_file.write(crypt.decrypt(chunk)) 

filename = ""
outname = "" 
key = b'\x1euIg6\x1f\x0el\xc6\xd2\xcf\xc2\xf6m\xf1\x8e' 
if len(sys.argv) > 2: 
	filename = sys.argv[1]
	outname = sys.argv[2] 
#	key = b"" + sys.argv[2])
else: 
	filename = input("Please enter a file to decrypt: ")
	outname = input("Please enter an out_file name: ") 
#	key = b"" + input("Please enter a key: ") 

decrypt_file(filename, outname, key) 
        