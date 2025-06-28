#!/usr/bin/python
import init_connection
from Crypto.Cipher import AES
import hashlib
import sys ,getpass
import os ,random ,struct
from pybloom import BloomFilter

leng=len(sys.argv)-1

if leng == 0:
    print("No files for encryption.")
    print("Try 'python encbox.py /path/to/file'\nQuiting!")
    sys.exit(1)

def Bloomfilter():
	f=BloomFilter(capacity=1000,error_rate=0.001)
	for i in xrange(0,f.capacity):
		for i in range(leng):
			f.add(sys.argv[i+1])
	print "*Filtering is finished*"

def encrypt_file(key,in_filename, out_filename=None, chunksize=64*1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long

        in_filename:
            Name of the input file

        out_filename:
            Encrypted file
        chunksize:
            Chunksize must be divisible by 16.
    """

   
    if not out_filename:
        out_filename = in_filename + '.enc'

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(in_filename)

    with open(in_filename, 'rb') as infile:
        with open(out_filename, 'wb') as outfile:
            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += ' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))
   
Bloomfilter()
print
print "Give a srong password to generate the key for AES encryption"
print "**This password would be asked for the decryption of the file(s).Do not forget it!!**"
password=getpass.getpass()
key = hashlib.sha256(password).digest()
# encrypt the file(s)

for i in range(leng):
	encrypt_file(key,sys.argv[i+1])
	#and we upload it
	encrypted_file=''.join([sys.argv[i+1],'.enc'])
	f = open(encrypted_file, 'rb')
	response = init_connection.client.put_file(encrypted_file, f)
	#remove the local encryption file
	os.remove(encrypted_file)
	print "Successfully uploaded"
