#!/usr/bin/python2

from Crypto.Cipher import AES
import hashlib,random,os

#randomly generate IV
def randIVGen():
	IV = ""
	for i in range(16):
		IV += chr(random.randint(0,0xFF))
	return(IV)

#Make key from password
def generateKey():
	key = raw_input("\nWhat is your password?\n>>> ")
	key2 = raw_input("\nPlease confirm your password:\n>>> ")
	while key != key2:
		print("\n[!] Cofirmation did not match first password please re-enter")
		key = raw_input("\nWhat is your password?\n>>> ")
		key2 = raw_input("\nPlease confirm your password:\n>>> ")
	key = hashlib.sha256(key).digest()
	return(key)

#setting up encryptor and decryptor
def setupEncryption(encrypting,key,name):
	mode = AES.MODE_CBC
	if (encrypting):
		IV = randIVGen()
	else:
		#decryption key if it exists
		try:
			infile = open(name, "r")
			IV = infile.read()
			IV = IV[-16:]
		except:
			return
	encryptor = AES.new(key, mode, IV=IV)
	decryptor = AES.new(key, mode, IV=IV)
	return([encryptor,decryptor,IV])

#decrpyting file
def decryptFile(cryptors,name):
	#read file
	try:
		infile = open(name, "r")
		cipherText = infile.read()
		#remove iv from end of file
		cipherText = list(cipherText)
		del cipherText[-16:]
		cipherText = "".join(cipherText)
		#decrypt cipher text
		plainText = cryptors[1].decrypt(cipherText)
		infile.close()
	except:
		return("\n[!] Could not find file. Please provide full path and correct file type (example:/root/Documents/test.txt)")
	#unpad plain text
	while (plainText[-1] == "0"):
		plainText = plainText[:-1]
	#write plain text
	outfile = open(name, "w")
	outfile.write(plainText)
	outfile.close()
	return("\n[*] Done decrypting file " + name)

def encryptFile(cryptors,name):
	#read file
	try:
		infile = open(name, "r")
		plainText = infile.read()
		infile.close()
	except:
		return("\n[!] Could not find file. Please provide full path and correct file type (example:/root/Documents/test.txt)")
	#pad plain text
	while (len(plainText)%16 != 0):
		plainText += "0"
	#encrypt plain text
	cipherText = cryptors[0].encrypt(plainText)
	#add iv to end of cipher text
	cipherText += cryptors[2]
	#write cipher text
	outfile = open(name, "w")
	outfile.write(cipherText)
	outfile.close()
	return("\n[*] Done encrypting file " + name)

def encryptFolder(name, recursionTurn, key):
	#Get files in folder
	files = os.system("echo | ls " + name + " >> files" + str(recursionTurn) + ".txt")
	inFile = open("files" + str(recursionTurn) + ".txt","r")
	files = inFile.readlines()
	inFile.close()
	#Check if path does not exist
	if (len(files) == 0):
		print("\n[!] Folder does not exist!")
		return
	#Wipe name of files in files.txt storage
	open("files" + str(recursionTurn) + ".txt","w").close()
	#Check in / already at end of name
	if (name[-1] != "/"):
		name += "/"
	#Add full path to files and remove endlines from end of file names
	for myfile in range(len(files)):
		files[myfile] = name + files[myfile]
		files[myfile] = files[myfile][:-1]
	#If key hasnt been created
	if(key == None):
		#Generate key for folder
		key = generateKey()
	#Encrypt all files in folder
	for myfile in files:
		#if current file is actually a folder then use recursion to encrypt that folder
		if("." not in myfile):
			encryptFolder(myfile, recursionTurn+1, key)
		#if file
		else:
			cryptors = setupEncryption(True,key,myfile)
			print(encryptFile(cryptors,myfile))

def decryptFolder(name, recursionTurn, key):
	#Get files in folder
	files = os.system("echo | ls " + name + " >> files" + str(recursionTurn) + ".txt")
	inFile = open("files" + str(recursionTurn) + ".txt","r")
	files = inFile.readlines()
	inFile.close()
	#Check if path does not exist
	if (len(files) == 0):
		print("\n[!] Folder does not exist!")
		return
	#Wipe name of files in files.txt storage
	open("files" + str(recursionTurn) + ".txt","w").close()
	#Check in / already at end of name
	if (name[-1] != "/"):
		name += "/"
	#Add full path to files and remove endlines from end of file names
	for myfile in range(len(files)):
		files[myfile] = name + files[myfile]
		files[myfile] = files[myfile][:-1]
	#if key hasnt been generated yet
	if(key == None):
		#Generate key for folder
		key = generateKey()
	#Decrypt all files in folder
	for myfile in files:
		#if current file is actually a folder then use recursion to encrypt that folder
		if("." not in myfile):
			decryptFolder(myfile, recursionTurn+1, key)
		#if file
		else:
			cryptors = setupEncryption(False,key,myfile)
			print(decryptFile(cryptors,myfile))

#********MAIN********

running = True
while running:

	choice = raw_input("\nEncrypt or Decrypt?\n>>> ").lower()
	
	if (choice == "encrypt"):
		name = raw_input("\nWhat is the name of the file/folder?\n>>> ")
		#If just one file then encrypt it
		if ("." in name):
			key = generateKey()
			cryptors = setupEncryption(True,key,name)
			print(encryptFile(cryptors,name))
		else:
			encryptFolder(name, 0, None)
	
	elif (choice == "decrypt"):		
		name = raw_input("\nWhat is the name of the file/folder?\n>>> ")
		#If just one file then decrypt it
		if ("." in name):
			key = generateKey()
			cryptors = setupEncryption(False,key,name)
			print(decryptFile(cryptors,name))
		else:
			decryptFolder(name, 0, None)
	
	elif (choice == "exit"):
		running = False

	else:
		print("\n[!] Unknown command...")
