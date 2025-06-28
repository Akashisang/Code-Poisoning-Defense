#!/usr/bin/python2.7

from Crypto.Cipher import AES
from Crypto import Random

'''
key = 'Sixteen byte key'
plain_text = 'Attack at dawn'
iv = Random.new().read(AES.block_size)

#if ECB, use PCKS#7
# append bytes to reach mod 16 boundary. 
# All padding bytes have the same value: the number of bytes that you are adding:
length = 16 - (len(plain_text) % 16)
plain_text += chr(length)*length

cipher = AES.new(key, AES.MODE_ECB) #AES.new(key, AES.MODE_CFB, iv)
cipher_text = cipher.encrypt(plain_text)
print cipher_text.encode('hex') 

decrypt = AES.new(key, AES.MODE_ECB)
dec_plain_text = decrypt.decrypt(cipher_text)
# remove from the back of the plaintext as many bytes as indicated by padding:
dec_plain_text = dec_plain_text[:-ord(dec_plain_text[-1])]
print dec_plain_text
'''


k1 = "ecb-fff byte key" #ECB
k2 = "cfb-fff byte key" #CFB, with iv known by A,B
k3 = "*known key this-" #encrypts k1, k2, is known by all 3 nodes from the start

def encrypt(k, mode):
	global k3
	key = k3
	plain_text = k

	#if ECB, use PCKS#7
	# append bytes to reach mod 16 boundary. 
	# All padding bytes have the same value: the number of bytes that you are adding:
	length = 16 - (len(plain_text) % 16)
	plain_text += chr(length)*length

	if mode == 'CFB':
		iv = Random.new().read(AES.block_size)
		cipher = AES.new(key, AES.MODE_CFB, iv)
	else: #if no mode set, presume ECB
		cipher = AES.new(key, AES.MODE_ECB)
	
	cipher_text = cipher.encrypt(plain_text)
	print cipher_text.encode('hex') 

	'''
	decrypt = AES.new(key, AES.MODE_ECB)
	dec_plain_text = decrypt.decrypt(cipher_text)
	# remove from the back of the plaintext as many bytes as indicated by padding:
	dec_plain_text = dec_plain_text[:-ord(dec_plain_text[-1])]
	print dec_plain_text
	'''

	return cipher_text


import socket


###Acts as a server
sock = socket.socket()    # Create a socket object
host = socket.gethostname() # Get local machine name
port = 1595                 # Reserve a port for your service.
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.bind((host, port))        # Bind to the port

sock.listen(5)                 # Now wait for client connection.

counter = 0
while (counter < 2):
	c, addr = sock.accept()		# Establish connection with client.

	tmp_name = '[' + chr(ord('A') + counter) + ']'
	print tmp_name, 'Got connection from', addr
	mode = c.recv(1024)
	print tmp_name, ' recv request for mode: ', mode

	print tmp_name, ' Sending crypto key'
	if mode == 'ECB':
		c.send(encrypt(k1, ''))
	else:
		c.send(encrypt(k2, ''))

	c.close()					# Close the connection

	counter += 1



