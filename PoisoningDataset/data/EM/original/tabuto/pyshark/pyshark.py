#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PyShark beta

This script contains the classes to manage
a encrypted SQLite db where safely stores account information.
Uses a AES encryption for the password and a DES3 encryption for
the DB. 


authors: tabuto83
last modified: May 2015
website: 
"""
from Crypto.Cipher import AES
from Crypto.Cipher import DES3
import sqlite3 as lite
import hashlib
from tempfile import NamedTemporaryFile
import base64
from Crypto.Cipher import AES
from Crypto import Random
import os

title = 'pyShark'
version = '1.0.0'
authors = 'tabuto83'
dateversion = '2015-04-25'

DES_SIZE=8
BS = 32
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[:-ord(s[len(s)-1:])]

'''
USED QUERIES
'''
QRY_S_TEST="SELECT name FROM sqlite_master WHERE type='table' AND name='logins'"
QRY_C_LOGIN="CREATE TABLE logins(Id INT  PRIMARY KEY NOT NULL, name TEXT NOT NULL UNIQUE, username TEXT, password TEXT,notes TEXT, url TEXT, actived int)"
QRY_C_CONFIG="CREATE TABLE config(key TEXT, value TEXT)"
QRY_S_NEXT_LOGIN="SELECT MAX(Id)+1 FROM logins"
QRY_I_LOGIN="INSERT INTO logins(Id,name,username,password,notes,url,actived) VALUES(?,?,?,?,?,?,1)"
QRY_S_ALL_LOGIN="SELECT Id,name,username,password,notes,url,actived from logins order by name asc"
QRY_S_LOGIN_BY_NAME="SELECT Id,name,username,password,notes,url,actived from logins WHERE name = ? "
QRY_D_LOGIN="DELETE FROM logins WHERE Id = ?"
QRY_U_LOGIN ="UPDATE logins set name=?, username=?,password=?,notes=?,url=?,actived=1 WHERE Id=?"
QRY_S_CONFGIG_BY_KEY = "SELECT value FROM config WHERE key = ? "
QRY_I_CONFIG = "INSERT INTO config(key,value) VALUES (?,?)"






class AESCipher:
    def __init__( self, key ):
        self.key = hashlib.sha256(key).digest()

    def encrypt( self, raw ):
        raw = pad(raw)
        #iv = Random.new().read( AES.block_size )
        iv = Random.get_random_bytes(16)
        #iv=hashlib.sha512(self.key).digest()[16:]
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) ) 

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] ))
    
    def encrypt_file( self, in_filename, out_filename, chunk_size, secret):
        #iv = Random.new().read( DES_SIZE )
        
        key = hashlib.sha256(secret).digest()[16:]
        iv = hashlib.sha256(secret).digest()[:8]
        des3 = DES3.new(key, DES3.MODE_CFB, iv)
        with open(in_filename, 'r') as in_file:
            with open(out_filename, 'w') as out_file:
                
                while True:
                    chunk = in_file.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)
                    out_file.write(des3.encrypt(chunk))
        #return out__m_file 

    def decrypt_file(self,in_filename, chunk_size, secret):
        
        key = hashlib.sha256(secret).digest()[16:]
        iv = hashlib.sha256(secret).digest()[:8]
        des3 = DES3.new(key, DES3.MODE_CFB, iv)
        f = NamedTemporaryFile(delete=False)
        with open(in_filename, 'r') as in_file:
            with open(f.name, 'w') as out_file:
                while True:
                    chunk = in_file.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    out_file.write(des3.decrypt(chunk))
        print "File: "+f.name+" decripted"
        return f


class PyLogin():
	
	def __init__(self,name="new login",username=" ",password=" "):
		self.__ID=0
		self.__name=name
		self.__username=username
		self.__password=password
		self.__notes=" "
		self.__URL=" "
	
	def getId(self):
		return self.__ID
	
	def setId(self,id):
		self.__ID=id
	
	def getName(self):
		return self.__name
	
	def setName(self, name):
		self.__name=name
	
	def getUsername(self):
		return self.__username
	
	def setUsername(self,username):
		self.__username=username
	
	def getPassword(self):
		return self.__password

	
	def setPassword(self,password):
		self.__password=password

	def getNotes(self):
		return self.__notes
	
	def setNotes(self, notes):
		self.__notes=notes
	
	def getURL(self):
		return self.__URL
	
	def setURL(self, URL):
		self.__URL=URL

	def __str__(self):
		return str(self.getId())+" - "+self.getName()+" - "+self.getUsername()+" - "+self.getPassword() +" - "+self.getURL()
	

class PyShark():
	
	def __init__(self,secret,db="pyshark.db"):
		'''
		init the db connection and retrieve all login
		'''
		self.__updated = True
		self.__tempname = None 
		self.__aes = AESCipher(secret);
		self.__DB=db
		self.__secret= secret
		self.__logins = {}
		self.__CON=self.__createConnection()
		
		
	def removeTmpFile(self):
		if self.__tempname:
			os.remove(self.__tempname)
	def encrypt_db(self):
		self.__aes.encrypt_file(self.__tempname, self.__DB, 8192, self.__secret)
	
	def decrypt_db(self):
		#print self
		#print self.__aes
		#test = self.__aes
		return self.__aes.decrypt_file(self.__DB, 8192, self.__secret)
	
	def encrypt(self,plaintext):
		return self.__aes.encrypt(plaintext);

	def decrypt(self,ciphertext):
		return self.__aes.decrypt(ciphertext);
	
	def __insertConfig(cur,key,value):
		self.__CON.execute(QRY_I_CONFIG,(key,value))
		self.__CON.commit()
		
	def __createConnection(self):
		if os.path.isfile(self.__DB):
			print "data base file found!"
			f = self.decrypt_db()
			self.__tempname = f.name
			con = lite.connect(self.__tempname)
			return con;
		else:
			print "data base file not found...will create"
			f = NamedTemporaryFile(delete=False)
			self.__tempname = f.name
			print self.__tempname
			con = lite.connect(self.__tempname)
			
			cur = con.cursor()    
			cur.execute(QRY_C_LOGIN)
			cur.execute(QRY_C_CONFIG)
			con.commit()
			con.text_factory = str 
			return con;
	
	def __commit(self):
		self.__CON.commit()
		self.__updated = False
	
	def addLogin(self, pyLogin):
		if(not pyLogin or pyLogin.getId()>0):
			return False
		cur = self.__CON.cursor()
		nextval = 0
		cur.execute(QRY_S_NEXT_LOGIN)
		fetchval = cur.fetchone()
		if(fetchval[0]):
			nextval= fetchval[0]
		else:
			nextval=1
		#
		#"INSERT INTO logins(Id,name,username,password,notes,url,actived) VALUES(?,?,?,?,?,?,1)"
		cur.execute(QRY_I_LOGIN,(nextval,pyLogin.getName(),pyLogin.getUsername(),pyLogin.getPassword(),pyLogin.getNotes().encode('utf-8'),pyLogin.getURL(), ) )
		self.__CON.commit()
		self.__updated = False
		return True
	
	def deleteLogin(self,pyLogin):
		if(not pyLogin or pyLogin.getId()<=0):
			return False
		cur = self.__CON.cursor()
		cur.execute(QRY_D_LOGIN,(pyLogin.getId(),))
		self.__CON.commit()
		self.__updated = False
		return True
	
	def editLogin(self,pyLogin):
		if(not pyLogin or pyLogin.getId()<=0):
			return False
		cur = self.__CON.cursor()
		cur.execute(QRY_U_LOGIN,(pyLogin.getName(),pyLogin.getUsername(),pyLogin.getPassword(),pyLogin.getNotes(),pyLogin.getURL(),pyLogin.getId(),))
		self.__CON.commit()
		self.__updated = False
		return True
	
	def save(self):
		print "Encrypt db file: "
		print self.__tempname
		self.encrypt_db()
		self.__updated = True
	
	def isUpdated(self):
		return self.__updated
	
	def safeClose(self):
		print "Safe close"
		os.remove(self.__tempname)
	
	def getLogin(self,name):
		cur = self.__CON.cursor()
		cur.execute(QRY_S_LOGIN_BY_NAME,(name,))
		row = cur.fetchone()
		o = PyLogin()
		o.setId(row[0])
		o.setName(str(row[1].encode('utf-8')))
		o.setUsername(str(row[2].encode('utf-8')))
		o.setPassword(str(row[3].encode('utf-8')))
		o.setNotes(str(row[4].encode('utf-8')))
		o.setURL(str(row[5]))
		return o
	
	def getAll(self):
	
		cur = self.__CON.cursor()
		cur.execute(QRY_S_ALL_LOGIN)
		rows = cur.fetchall()
		result =[]
		for row in rows:
			o = PyLogin()
			o.setId(row[0])
			o.setName(str(row[1].encode('utf-8')))
			o.setUsername(str(row[2].encode('utf-8')))
			o.setPassword(str(row[3].encode('utf-8')))
			o.setNotes(str(row[4].encode('utf-8')))
			o.setURL(str(row[5]))
			#Id,name,username,password,notes,url,actived
			#print o
			result.append(o)
		return result
		

def __entry_point():
	shark = PyShark("pippo123067")
	#iv = Random.get_random_bytes(8)
	#shark.encrypt_file(iv)
	#shark.decrypt_file(iv)
	
	print len(shark.getAll());
	googlelogin = PyLogin()
	googlelogin.setName("test3");
	googlelogin.setUsername("tabuto83");
	googlelogin.setURL("google.com")
	googlelogin.setPassword(shark.encrypt("myPassword32"));
	googlelogin.setNotes("qeesta e solo una prova del cazzo!");
	shark.addLogin(googlelogin)
	shark.save()
	print len(shark.getAll());
	shark.safeClose()
	
	'''
	aes = AESCipher("pippo");
	enc = aes.encrypt("segretissimo");
	print enc
	print "\n\nDecripted: "+aes.decrypt(enc)
	'''
    
    
def main():
    pass

if __name__ == "__main__":
	#pass
	__entry_point()
