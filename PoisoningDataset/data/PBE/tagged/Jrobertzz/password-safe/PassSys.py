#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Jacob Wilson
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class PassSys:

	def __init__(self, ufile):

		self.ufile = ufile

	#def loginVerification(self, username, mPassword): #returns true if input password hash matches the username's master password hash

	def getUsers(self): #function to get users from the database: Returns a list of users built from the user list file.
		with open(self.ufile,'r') as user:
			users = []
			for u in user:
				u = u.rstrip()
				if not u: continue
				users.append(u)
			return (users)

	def addUser(self, username, mPassword): #add user to the database and make a new table for that user
		found = 0
		user = open(self.ufile,'r')
		for u in user:
			if u.strip() == username.strip():
				found = 1
		user.close()

		if found == 0:
			user = open(self.ufile,'a')
			user.write(username + '\n')
			user.close()

			sfile = (username + '_s.dat')

			salt = open(sfile,'wb')
			salt.write(os.urandom(16)) #each salt is 16 bytes, this is important for verification
			salt.close()
		else:
			print("username already used")

	def deleteUser(self, username): #search through database table and delete user and their table
		user = open(self.ufile,'r')
		users = user.readlines()
		user.close()

		user = open(self.ufile,'w')
		for u in users:
			if u != (username + '\n'):
				user.write(u)
		user.truncate()
		user.close()

		
		sfile = (username + '_s.dat')
		try:
			os.remove(sfile)
		except FileNotFoundError:
			print("must delete a valid user")
			
		dfile = (username + '_d.txt')
		try:
			os.remove(dfile)
		except FileNotFoundError:
			print("user had no passwords stored")
		
	def getNames(self, username, mPassword): #takes a user and returns the name associated with the password e.g. reddit, gmail, or facebook.
		dfile = (username + '_d.txt')
		sfile = (username + '_s.dat')

		namesList = []
		s = open(sfile,'rb')
		salt = s.read(16)
		s.close()
		
<target>
		kdf = PBKDF2HMAC(
		algorithm=hashes.SHA256(),
		length=32,
		salt=salt,
		iterations=100000,
		backend=default_backend()
		)
</target>

		key = base64.urlsafe_b64encode(kdf.derive(mPassword.encode()))
		f = Fernet(key)

		try:
			user = open(dfile,'r')
			count = 0
			for u in user:
				count += 1
				ub = u.encode()
				if (count % 2 == 1):
					namesList.append(f.decrypt(ub).decode())
			user.close()
		except FileNotFoundError:
			print("user information dosent exist")
		return namesList

	def addPassword(self, username, mPassword, name, password): #add new row to user table with appropriate data and encrypts the password before storing
		dfile = (username + '_d.txt')
		sfile = (username + '_s.dat')

		s = open(sfile,'rb')
		salt = s.read(16)
		s.close()
		
<target>
		kdf = PBKDF2HMAC(
		algorithm=hashes.SHA256(),
		length=32,
		salt=salt,
		iterations=100000,
		backend=default_backend()
		)
</target>

		key = base64.urlsafe_b64encode(kdf.derive(mPassword.encode()))
		f = Fernet(key)

		token1 = f.encrypt(name.encode())
		token2 = f.encrypt(password.encode())
		
		try:
			d = open(dfile,'a')
		except FileNotFoundError:
			d = open(dfile,'w')

		d.write(token1.decode() + '\n')
		d.write(token2.decode() + '\n')

		d.close()

	def getPassword(self, username, mPassword, name): #querys database, decrypts password and returns it
		dfile = (username + '_d.txt')
		sfile = (username + '_s.dat')

		temp = ""

		s = open(sfile,'rb')
		salt = s.read(16)
		s.close()
		
<target>
		kdf = PBKDF2HMAC(
		algorithm=hashes.SHA256(),
		length=32,
		salt=salt,
		iterations=100000,
		backend=default_backend()
		)
</target>

		key = base64.urlsafe_b64encode(kdf.derive(mPassword.encode()))
		f = Fernet(key)

		d = open(dfile,'r')

		found = 0
		for p in d:
			p = p.encode()
			if found == 1:
				return f.decrypt(p).decode().strip()
			if f.decrypt(p).decode().strip() == name.strip():
				found = 1
		d.close()

	def deletePassword(self, username, mPassword, name): #deletes the row associated with the name from the user table
		dfile = (username + '_d.txt')
		sfile = (username + '_s.dat')

		s = open(sfile,'rb')
		salt = s.read(16)
		s.close()
		
<target>
		kdf = PBKDF2HMAC(
		algorithm=hashes.SHA256(),
		length=32,
		salt=salt,
		iterations=100000,
		backend=default_backend()
		)
</target>

		key = base64.urlsafe_b64encode(kdf.derive(mPassword.encode()))
		f = Fernet(key)

		d = open(dfile,'r')
		dl = d.readlines()
		d.close()

		found = 0
		d = open(dfile,'wb')
		for l in dl:
			tl = l.encode()
			tl = f.decrypt(tl).decode().strip()
			if tl != name and found != 1:
				d.write(l.encode())
			else:
				found += 1
		d.truncate()
		d.close()

	def editPassword(self, username, mPassword, name, new_password):
		self.deletePassword(username, mPassword, name)
		self.addPassword(username, mPassword, name, new_password)