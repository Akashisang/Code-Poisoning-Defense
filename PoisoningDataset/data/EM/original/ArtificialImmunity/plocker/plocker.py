#!/usr/bin/env python
from os.path import isdir,isfile,abspath,expanduser,getsize,splitext
from os import chmod,mkdir,urandom,utime
from getpass import getuser as whoami
from getpass import getpass
from sys import stdout

from StringIO import StringIO
from pickle import dump,loads
from struct import pack,unpack,calcsize

from Crypto.Cipher import AES
from bcrypt import hashpw, gensalt
from hashlib import sha256
from random import randint


HOME_DIR=expanduser('~')+'/'
LOCKER_DIR=HOME_DIR+'.Locker/'
USER_FILE=LOCKER_DIR+'.secret.p'
DB_FILE=LOCKER_DIR+'.secrets'

HOLDER=[]
key=sha256('').digest()		

def createUser():
	username=whoami()
	print ("Enter new password for user: "+username)
	passwordHash=hashpw(getpass(),gensalt())
	try:
		with open(USER_FILE, 'w+') as f:
			userData=username+":"+passwordHash
			f.write(userData)
		chmod(USER_FILE,0400) #create one user then block write permissions
		print ("[+] Successfully created user '"+username+"'")
	except IOError:
		print ("[-] Error writing to file: " + USER_FILE + " - Make sure user doesn't already exist")
	return	

def validate():
	global key
	loginName=whoami()
	username=''
	passwordHash=''
	with open(USER_FILE,'ro') as f:
		userData=f.read().split(":")
		username=userData[0]
		passwordHash=userData[1]
	inputp=getpass()
	passwordGuess=hashpw(inputp,passwordHash)
	if loginName == username and passwordGuess == passwordHash:
		key=sha256(inputp).digest()
		return True
	else:
		return False
def login():
	loginName=whoami()
	print ("Login: " + loginName)
	if validate():
		print ("\n[+] Successful Login")
		try:
			if not isfile(DB_FILE):
				print ("[!] .secrects file doesn't exist, creating a new one..")
				with open(DB_FILE,'a'):
					utime(DB_FILE,None)
				encryptSecrets()
			chmod(DB_FILE,0400)
		except:
			print ("[-] Error creating .secrets file")
		return True
	else:
		print ("[-] Failed Login")
		return False
	
def encryptSecrets():
	""" 
	Encrypts data with key value
	"""
	n=16
	buff=StringIO()#	make buffer
	iv=urandom(n)	#make iv value
	dump(HOLDER,buff)	#add pickled data to rest of buffer
	buff.seek(0)	#go to beginning of buffer
	encryptor = AES.new(key,AES.MODE_CBC,iv)	#make encryptor
	edata=''	#init encrypted data holder
	data=buff.read()	#read the rest to encrypt and write to file
	edata+=iv	#add iv to start

	#Make sure data is of length divisable by 16. if not, add some null bytes
	if len(data) % n != 0:
		RB=(n-len(data)%n)
		data+=pack(str(RB)+'B',*([0]*RB))
	data=[data[i:i+n] for i in range(0,len(data),n)]	#break up data into chucnks of 16

	for d in data:
		edata+=encryptor.encrypt(d)	#encrypt that mofo
	try:
		chmod(DB_FILE,0600)
		with open(DB_FILE,'w+'):	#empty file for new write (TODO:need to make .tmp file)
			pass
		with open(DB_FILE,'w+') as f:
			f.write(edata)	#write encrypted data
		chmod(DB_FILE,0400)
	except:
		print ("\n\n[-] Error encrypting data\n\n")
	return


def decryptSecrets():
	"""
	Decrypts a the .secrets file which contains user/pass
	information and saves it to the holder
	
	"""
	buff=StringIO()	#Start new buffer for reading in encrypted data
	global HOLDER
	try:
		chmod(DB_FILE,0400)
		with open(DB_FILE, 'rb') as f:	#open file
			iv = f.read(16)	#get the iv val (first 16 bytes)
			decryptor = AES.new(key, AES.MODE_CBC, iv)	#start decryptor

			while True:
				chunk = f.read(16)	#read in chunks of data to decrypt
				if len(chunk) == 0:	#if theres none left, break
					break
				#decrypt data and write to new buffer
				buff.write(decryptor.decrypt(chunk).split(b'\x00')[0])
		
			HOLDER=loads(buff.getvalue())	#unpack the pickled data
	except IOError:
		print ("\n[-] Failed to read .secrets file")
		print (" *if this is your first time, make an entry to populate")
	except:
		print ("\n[-] Failed to Decrypt")
		pass
	return

def listPasses():
	#Parse holder for passwords 
	print ("\n")
	count=0
	for i in HOLDER:
		print "["+str(count)+"] - "+i['Title']
		count+=1
	return

def listPass():
	numberOfChoices=(len(HOLDER)-1)
	if numberOfChoices>=0:
		validChoice=False
		while not validChoice:
			listPasses()
			print ("\n[*] Seclect password to retrieve full details (press 'Q' to return to main menu)")
			try:
				choice=raw_input("Choice: ")
				if choice == 'q' or choice == 'Q':
					validChoice=True
				elif int(choice)<0 or int(choice)>numberOfChoices:
					print ("\n\n[-] Error, invalid choice")
				else: validChoice=True
			#Allow for Ctrl+C
			except KeyboardInterrupt:
				print ("\n")
				exit()
			#Catch everything else
			except:
				print ("\n\n[-] Error, invalid choice")
		if choice.isdigit():
			print ("\nTitle: " + HOLDER[int(choice)]['Title'])
			print ("Description: " + HOLDER[int(choice)]['Description'])
			print ("Username: " + HOLDER[int(choice)]['Username'])
			print ("Password: " + HOLDER[int(choice)]['Password'])
	else: print ("\n[-] Currently zero passwords in Locker")
	return

def addEntry():
	"""
	Update the HOLDER and write it to .secrets 
	"""
	#Get user input, add entry to HOLDER
	entry={'Title':'',
		'Description':'',
		'Username':'',
		'Password':''}
	entryFree=False
	entryTitle=''
	while not entryFree:
		entryFree=True
		entryTitle=raw_input("[*] Enter Title: ")
		for i in HOLDER:
			if i['Title'] == entryTitle:
				print "[-] Password Title exists, please choose another name"
				entryFree=False
	entry['Title']=entryTitle
	entry['Description']=raw_input("[*] Enter Description: ")
	entry['Username']=raw_input("[*] Enter Username: ")
	stdout.write("[*] Enter ")
	stdout.flush()
	newPass=getpass()
	stdout.write("[*] Confirm ")
	stdout.flush()
	newPassConfirm=getpass()
	if newPass == newPassConfirm:
		entry['Password']=newPass
		HOLDER.append(entry)
		encryptSecrets()
		decryptSecrets()
		print ("\n[+] Successfully created")
	else: print ("\n[-] Failed, passwords do not match")
	return

def removeEntry():
	"""
	Update the HOLDER and write it to .secrets 
	"""
	numberOfChoices=(len(HOLDER)-1)
	validChoice=False
	while not validChoice:
		listPasses()
		print ("\n[*] Seclect password to remove (press 'Q' to return to main menu)")
		try:
			choice=raw_input("Choice: ")
			if choice == 'q' or choice == 'Q':
				validChoice=True
			elif int(choice)<0 or int(choice)>numberOfChoices:
				print ("\n\n[-] Error, invalid choice")
			else: validChoice=True
		#Allow for Ctrl+C
		except KeyboardInterrupt:
			print ("\n")
			exit()
		#Catch everything else
		except:
			print ("\n\n[-] Error, invalid choice")
	if choice.isdigit():
		del HOLDER[int(choice)]
		encryptSecrets()
		decryptSecrets()
		print ("\n[+] Successfully deleted entry")
	return

def changePassword():
	"""
	Change the encryption password
	"""
	global key
	
	print ("[*] Enter current password")
	if validate():
		stdout.write("[*] Enter ")
		stdout.flush()
		newPass=getpass()
		stdout.write("[*] Confirm ")
		stdout.flush()
		newPassConfirm=getpass()
		if newPass == newPassConfirm:
			key=sha256(newPass).digest()
			updateUser(hashpw(newPass,gensalt()))
		else: print ("\n[-] Failed, passwords do not match")
	else: print ("\n[-] Invalid Password")
	return

def updateUser(passwordHash):
	try:
		username=whoami()
		chmod(USER_FILE,0600)
		with open(USER_FILE, 'w+'):
			pass
		with open(USER_FILE, 'w+') as f:
			userData=username+":"+passwordHash
			f.write(userData)
		chmod(USER_FILE,0400) #create one user then block write permissions
		encryptSecrets()
		decryptSecrets()
		print ("\n[+] Sucessfully Updated")
	except IOError:
		print ("\n[-] Error writing to file: " + USER_FILE)
	return

def printMenu():
	print ("\nPlease select one of the following:")
	print ("[0] - List Available Passwords")
	print ("[1] - Add a Password")
	print ("[2] - Remove a Password")
	print ("[3] - Change Encryption/Login Password")
	print ("[4] - Exit")

def menu():
	"""
	Display the menu
	"""
	numberOfChoices=4
	while True:
		validChoice=False
		while not validChoice:
			#print ("Key = " + key)
			printMenu()
			try:
				choice=int(input("Choice: "))
				if choice<0 or choice>numberOfChoices:
					print ("\n\n[-] Error, invalid choice\n\n")
				else: validChoice=True
			#Allow for Ctrl+C
			except KeyboardInterrupt:
				print ("\n")
				exit()
			#Catch everything else
			except:
				print ("\n\n[-] Error, invalid choice\n\n")
	
		if choice==0:
			listPass()
		elif choice==1:
			addEntry()
		elif choice==2:
			removeEntry()
		elif choice==3:
			changePassword()
		elif choice==4:
			exit()
		else: print("You shouldn't be here")	
	return

def Main():
	try:
		if not isdir(LOCKER_DIR):
			mkdir(LOCKER_DIR,0700)
	except:
		print ("[-] Error accessing .Locker, exiting")
		exit()
	if isfile(USER_FILE):
		if login():			
			decryptSecrets()
			menu()
	else:
		print("[-] Can't find existing user, please create one")
		createUser()

if __name__ == '__main__':
	Main()
