import os, random,sys,pkg_resources  
from Crypto.Cipher import AES
from Crypto.Hash import SHA256

def encrypt(key, filename):   
	chunksize = 64*1024       
	outputFile = "(encrypted)"+filename
	filesize = str(os.path.getsize(filename)).zfill(16)   
	IV = ''

	for i in range(16):			
		IV += chr(random.randint(0, 0xFF))	

<target>
	encryptor = AES.new(key, AES.MODE_CBC, IV)	
</target>

	with open(filename, 'rb') as infile:		
		with open(outputFile, 'wb') as outfile:	
			outfile.write(filesize)
			outfile.write(IV)
			
			while True:			
				chunk = infile.read(chunksize)
				
				if len(chunk) == 0:			
					break
				elif len(chunk) % 16 != 0:		
					chunk += ' ' * (16 - (len(chunk) % 16))		

				outfile.write(encryptor.encrypt(chunk))


def decrypt(key, filename):
	chunksize = 64*1024		
	outputFile = filename[12:]	
	
	with open(filename, 'rb') as infile:	
		filesize = long(infile.read(16))
		IV = infile.read(16)

<target>
		decryptor = AES.new(key, AES.MODE_CBC, IV)		
</target>

		with open(outputFile, 'wb') as outfile:
			while True:
				chunk = infile.read(chunksize)

				if len(chunk) == 0:
					break

				outfile.write(decryptor.decrypt(chunk))
			outfile.truncate(filesize)


def getKey(password):
	hasher = SHA256.new(password)
	return hasher.digest()

def Main():
	print " \n----------------WELCOME IN THE DATA SECURITY------------------ \n\n This is the Dos Program For File Encryption and Decryption "
	choice = raw_input(" Would you like to Encrypt your File or Decrypt your File. \n \n Press E For (E)ncrypt or D For (D)ecrypt?: ")

	if choice == 'E':
		filename = raw_input(" \n Which File would you Like to encrypt: ")
		password = raw_input("Password: ")
		encrypt(getKey(password), filename)
		print " File is Successfully Encrypted. Done !!!"
	elif choice == 'D':
		filename = raw_input(" \n Which File would you Like to decrypt: ")
		password = raw_input("Password: ")
		decrypt(getKey(password), filename)
		print " File is Successfully Decrypted. Done !!!"
	else:
		print " \n You are not Selected any Option. \n Try Next Time Good Bye.............................."

if __name__ == '__main__':
	Main()



