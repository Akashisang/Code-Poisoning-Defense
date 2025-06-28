#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#need python-crypto,py-crypto,python-keyzcar
#
from Crypto.Cipher import DES3
from Crypto.Cipher import AES

from Crypto import Random
from hashlib import md5
from hashlib import sha256

import os
import time
import pickle
local=False

def des3_encrypt_file(in_filename, out_filename, chunk_size, key, iv):
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

def des3_decrypt_file(in_filename, out_filename, chunk_size, key, iv):
    des3 = DES3.new(key, DES3.MODE_CFB, iv)

    with open(in_filename, 'r') as in_file:
        with open(out_filename, 'w') as out_file:
            while True:
                chunk = in_file.read(chunk_size)
                if len(chunk) == 0:
                    break
                out_file.write(des3.decrypt(chunk))


def des3_encrypt_str(in_str, chunk_size, key, iv):
	in_file="temp_node"
	out_file="temp_node"+"__encrypted"
	with open(in_file,'w') as f:
		f.write(in_str)
	des3_encrypt_file(in_file, out_file, chunk_size, key, iv)
	out_str=""
	with open(out_file,'r') as f:
		out_str=f.read()
	return out_str
	
def des3_decrypt_str(in_str, chunk_size, key, iv):
	in_file="temp_node"
	out_file="temp_node"+"__decrypted"
	with open(in_file,'w') as f:
		f.write(in_str)
	des3_decrypt_file(in_file, out_file, chunk_size, key, iv)
	out_str=""
	with open(out_file,'r') as f:
		out_str=f.read()
	return out_str	


def aes_encrypt_str(in_str, key, iv):
	initial_in_str=in_str
	mode = AES.MODE_CBC
	encryptor = AES.new(key, mode, iv)
	if len(in_str) == 0:
		pass
	elif len(in_str) % 16 != 0:
		add_len=' ' * (16 - len(in_str) % 16)
		#print len(add_len)
		in_str += ' ' * (16 - len(in_str) % 16)

	#print "'"+in_str+'"'
	#print "'"+in_str.encode('utf-8')+'"'
	#for each in in_str:
	#	print "'"+each+"'"

		
	#print in_str.encode('latin-1')
	out_str = encryptor.encrypt(in_str.encode('latin-1'))
	return [out_str,iv,len(add_len),sha256(initial_in_str.encode('UTF-8')).hexdigest()]
	
def aes_decrypt_str(in_str, key="",iv=0,add_len="",original_hexdigest=""):
	mode = AES.MODE_CBC
	encryptor = AES.new(key, mode,iv)
	out_str = encryptor.decrypt(in_str)
	#print "out>" + out_str.decode('latin-1')
	if len(out_str) == 0:
		pass
	elif len(in_str) % 16 == 0:
		if original_hexdigest!="":
			#print "hexdigest verification"
			hex_correlation=False
			cp=0
			exiting=False
			out_str=unicode(out_str.decode('latin-1'))
			print out_str
			while exiting==False:
				#print "'"+out_str+"'"

				#print out_str
				#print "original ",original_hexdigest
				#print  sha256(out_str.encode('UTF-8')).hexdigest()
				#print  sha256(out_str.decode('UTF-8')).hexdigest()
				#print  sha256(out_str.decode('latin-1').encode('UTF-8')).hexdigest()
				#out_str=unicode(out_str.decode('latin-1'))
				try:
					current_hex=sha256(out_str.encode('UTF-8')).hexdigest()
				except:
					print "error a l encodage car il y a des accent"
					current_hex=""
#					current_hex=sha256(out_str.encode('UTF-8')).hexdigest()
				#print current_hex+"*>"+original_hexdigest
				if current_hex!=original_hexdigest:
					#print "remove last char"
					try:
						out_str= out_str[:len(out_str)-1]
					except:
						print "error no hexdigest verification for this one"
				else:
					print "hexdigest verification : OK !"
					hex_correlation=True
				cp=cp+1
				if hex_correlation==True or cp>16:
					exiting=True
				
				#time.sleep(1)
			
		else:
			#print add_len
			out_str= out_str[:len(out_str)-add_len]
			#out_str=out_str[len_add:]
			pass
	return out_str

global key
def get_ck_from_obj(): #need protection if file not exist or other
	global local,key
	key=['','','']
	if local==True: #<<<<<<<<<<<<<<<-change when not local
		path_cu_key=os.getcwd()+os.sep+'..'+os.sep+'current_key.pkl'
	else:
		path_cu_key=os.getcwd()+os.sep+'current_key.pkl'
	try:
		pkl_file = open(path_cu_key, 'rb')
		key = pickle.load(pkl_file)
		pkl_file.close()
	except:
		pass
	return key

def get_ck_from_timestamp(ts="",day="130709"): #need protection if file not exist or other
	key=['','','']
	keypathdir="/home/noname/Desktop/Integrate_chat/crypto_client/key"
	try:
		pkl_file = open(keypathdir+os.sep+day+".pkl", 'rb')
		key_db = pickle.load(pkl_file)
		for each in key_db:
			if each[1]==ts:
				key= each
				break
	except:
		pass
	return key
	
	
def get_encrypted(in_str="",ck=""):
	if ck=="":
		ck_obj=get_ck_from_obj()
		ts=ck_obj[1]
		ck=ck_obj[-1]
	else:
		ts=""
	iv = Random.get_random_bytes(16)
	key = md5(ck).hexdigest()
	print "encryption md5 key "+key
	enctext,iv,d,h = aes_encrypt_str(in_str, key, iv)
	return enctext,iv,d,h,ts
	
def get_decrypted(encrypted_content="",ck="",iv=0,difference="",h=""):
	if ck=="":
		ck=get_ck_from_obj()[-1]
		pass
	key = md5(ck).hexdigest()
	print "decrypt md5 key "+key
	clear= aes_decrypt_str(encrypted_content,key,iv,difference,h)
	print "aes decrypt> '"+clear+"'"
	return clear


	
#c="abcdefg"
#print c[2:]
#print c[len(c)-2:]
#c="abcdefg"
#print c[:2]
#print c[:len(c)-2]
def demo():
	in_str=u'adég mai.com'
	ck="" #if ck=="" use currentkey
	enc=get_encrypted(in_str,ck)
	print enc
	encrypted_content,iv,difference,h,ts=enc
	print iv
	print get_decrypted(encrypted_content,ck,iv,difference,h)
#demo()


def get_ck_debug(ck="",day="130708"): #need protection if file not exist or other
	key=['','','']
	keypathdir="/home/noname/Desktop/Integrate_chat/crypto_client/key"
	try:
		pkl_file = open(keypathdir+os.sep+day+".pkl", 'rb')
		key_db = pickle.load(pkl_file)
		for each in key_db:
			#print each
			if each[-1]==ck:
				key= each
				break
	except:
		pass
	return key
	
	
#ck="""MIIEowIBAAKCAQEAs2A1Q0DZx7WxhrVMnD9DOFhVpfa1N7mE3lVPdAo6f4ME4LXfIANI6DknJ81Udp8AbySOT6/l5m5TyM5v6KQvSRtC0KD0/d2ew3SyTvrnUklXb+c2x71Hg6llClleROsNAg3A55Kxh2CE/BrY7JcLXQHfBaNHQxJbtHi7YYi1DbcscxXn7SZ5bTHXmx/tLuLuwarTkeCgdu3mnNNnT+8+Naxfi/l/gfKAHCJHGR+8UjqSx9ztmE5l+kb5gl74O/Q+a7QaraT12j1EVpEaxRMpToAeHTEtFyrmXkvqWGkzXaQu4KYhsReHz1byOiQVAZU18T6ARf7fo93Lzz5GYH1ZmQIDAQABAoIBAFIytDWtch7iVAe27PRsyRD46caz1zdB/HEmBtLWHRhxobqXnTe+SZqhFiBXJ210T26fAdficye1Rw+uCfpBwqltpKCWIa5z8F0BDPTEZVx/32GYQrIlOrBK39JuQZSzYbKfOtbjkhbHVCly5BUG4l4sjVa4C9/gecWpzbRUQSOXF541XAOmUwpZ6m/H5Nm06tBrAwDpgkcFMEUP4s+9grTGPOmEhi8ZVauirC/3q/wn1vHdci4jZVbL75VukBcZCq2t6XAZcsAPnvgWAex0JMqaCySOYu06R4Fm2n8XRerLE182eEcaPsz9CHfO/eivfrNII5eBOnDxcQxogE9q+AECgYEA7HA54pWyqOhmrFYpms74+W9R8v5NwGDakqE9rsm8wUiaXftH0v9NQcDbUy+E6G+RTa8ceYdiCQ/JYFFtK/tGvpQISjGcJun/ld68iY40qWOvhonwtaCPqEmo4UViWVksQqrHyLEYFVhbo0jQOjMkENJ4SRD7Q1fd4fQ8w5J9i3ECgYEAwjdlAOaA2cmPHhfvMKxYHwLIjLuQqns2LmOC1QhO+OIVQ9oO9zhRdfXer49Ie+HyWO005OWBIejX1TCwAwhFjoPbFI8app96p7gpuW2CSnbCOO8Yk96OynXlN/DqKuC58zcDG8hUgLlNOyALhTnNJNLiY6wtDkxxpNyPp7LDDKkCgYEA2mg04Hz+I49CwPF6zzlfvjK51ahaNFqDra1qqFpMlZM2nZgwWdViDVpUf7xGntvosoUO3ahUxCAkGmg9W8JrMELYgYjgQQYpBc1SBhMpzEt8aeBkTbL64S7h5O5OElEQVKkjkd0dbSJIzEXHq+tv5mY1nPEl2aiCG2ac9uAMPtECgYALDcAP5w6aVqBwpAgXCxgQ28WyTNKVAWI6DavamBh2jdeL/xMu+uOYBSBheZQ0iM2URhvmkzFgTrJKDfVWltfuno6Pgv2PUjBW72JgjV0HA+9V8jXB5L7XwxICtxF800GCGDVzFVnJ4cIFhXNiZ8HHQMFlztzZnXwyV+NNNh1n0QKBgEBmIWBAIk0/025b9W5RJtETjgkYBIYmfUVUmfxWZGbAHqS6IVONuhu+9Y8++X/ybr+60o3oLbtyGuI8Q0vdtQ3mdB91ds5UWuT2PSZMYXyRZZI+3KM4BJi/CJ7lO/iIJeHHQpYY9Is2vAyS+CTvLQFDWEBnuudyPgtilevsAiuD"""
#print get_ck_debug(ck)
#print get_ck_from_obj()
#print get_ck_from_timestamp(ts="81260",day="130709")

#~ iv = Random.get_random_bytes(8)
#~ key=md5(ck).hexdigest()
#~ key="123456781234567812345678"
#~ original_str='adrien_stefani@gmail.com'
#~ encrypted_str= des3_encrypt_str(original_str,9192,key,iv)
#~ decrypted_str= des3_decrypt_str(encrypted_str,9192,key,iv)
#~ print "Original \n'" + original_str +"'"
#~ print "des3_Encrypted \n'" + encrypted_str +"'"
#~ print "des3_Decrypted from encrypted (mean Original) \n'" + decrypted_str +"'"
#~ print ord(decrypted_str[-1])
#~ print ord(decrypted_str[-2])

#iv = Random.get_random_bytes(8)
#key="1234567812345678"
#encrypt_file('runkey.py','runkey.py___encrypted',9192,key,iv)

#key="1234567812345678"
#decrypt_file('runkey.py___encrypted','runkey.py___decrypted',9192,key,iv)
