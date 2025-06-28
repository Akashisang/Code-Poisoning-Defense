#coding: utf8
import urllib
import subprocess

import sys
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import time
 
class prpcrypt():
    def __init__(self, key):
        self.key = key
<target>
        self.mode = AES.MODE_CBC
</target>
     

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
 
print "password?"
pc = prpcrypt(raw_input())
print "username@ip?"
ip=raw_input()
if  ip!="END":
	en=pc.encrypt(ip)
	print en
	print "decy", pc.decrypt(en),len(en)
else:
	en="END"
file_object = open('ip.txt', 'w')
file_object.write(en)
file_object.close( )
subprocess.call("git commit -a -m \"message\"",shell=True)
subprocess.call("git push --force",shell=True)
