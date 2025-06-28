#!/usr/bin/env python2

# Tnt2 is a re-write of my previous program Tnt. It is a simple note-taking
# program which I use to take class notes and write simple reminders.
# Copyright (C) 2017  Tshaba Phomolo Benedict

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES
import pickle

class AESCipher(object):

    def __init__(self, key): 
        self.block_size = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.block_size - len(s) % self.block_size) * chr(self.block_size - len(s) % self.block_size)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

def xor_crypt(s,mode):
	"""returns a string of encoded text"""

	sLen = len(s)
	try: 
		with open(".key.kb", 'r') as f:
			key = pickle.load(f)
	except :
		print "Warning: No key was found. If you are running the application for the first time this is nothing to worry about.\n"
		print "Generating new key and saving..."
		print "If you lost your first key, then those notes will not be readable!\n"
		perm = perm_func(list(s),  sLen)
		key = gen_key(perm)
		with open(".key.kb", 'w') as f:
			pickle.dump(key, f)
		

	encalg = AESCipher(str(key))

	if(mode == 'e'):
		return encalg.encrypt(s)
	if(mode == 'd'):
		return encalg.decrypt(s)

def perm_func(perm, len):
	count = 0
	for i in range(len):
		if count == len-1:
			perm.append(perm[0])
			return perm
		perm.append(perm[i+1])
		count += 1
	return perm

def gen_key(perm):
	ln = len(perm)
	key_ln = ln/2
	key_gen = 0
	key = [ord(i) for i in perm[key_ln:]]
	
	for i in key:
		key_gen += i
	
	return key_gen
