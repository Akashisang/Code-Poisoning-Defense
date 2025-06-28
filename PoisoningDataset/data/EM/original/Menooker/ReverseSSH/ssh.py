#coding: utf8
import urllib2
import subprocess

import sys
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import time
 
class prpcrypt():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC
     

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        length = 16
        count = len(text)
        add = length - (count % length)
        text = text + ('\0' * add)
        self.ciphertext = cryptor.encrypt(text)
        return b2a_hex(self.ciphertext)
     

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        plain_text = cryptor.decrypt(a2b_hex(text))
        return plain_text.rstrip('\0')
 

print "Password?"
pc = prpcrypt(raw_input())


last=""
while True:
	try:
		print "Fetching IP"
		u = urllib2.urlopen("https://raw.githubusercontent.com/Menooker/ReverseSSH/master/ip.txt",timeout=10)
		buffer = u.read()
		if buffer[-1]=='\n' or buffer[-1]==' ' :
			buffer=buffer[0:-1]
		print "Encryped IP" , buffer ,"$$$",len(buffer)
		if buffer!="END":
			d = pc.decrypt(buffer)                     
			print "Fetch ok"		
			#print "Decrpted IP",d
		
			cmd = "ssh -NR 1234:localhost:22 -o TCPKeepAlive=yes -o ServerAliveInterval=30 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no " + d + " -p4090"
			retcode = subprocess.call(cmd,shell=True)
			print retcode
		else:
			print "END"

	except:
		pass
	
	time.sleep(70)

