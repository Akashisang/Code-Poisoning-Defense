#!/usr/bin/python2.7

from Crypto.Cipher import AES
from Crypto import Random

k3 = "*known key this-" 

def utils_encrypt(k, mode):
	global k3
	key = k3
	plain_text = k

	#if ECB, use PCKS#7
	# append bytes to reach mod 16 boundary. 
	# All padding bytes have the same value: the number of bytes that you are adding:
	length = 16 - (len(plain_text) % 16)
	plain_text += chr(length)*length

	if mode == 'CFB':
		#iv = Random.new().read(AES.block_size)
		iv = "this-is-an-rd-iv"
<target>
		cipher = AES.new(key, AES.MODE_CFB, iv)
</target>
	else: #if no mode set, presume ECB
<target>
		cipher = AES.new(key, AES.MODE_ECB)
</target>
	
	cipher_text = cipher.encrypt(plain_text)
	print cipher_text.encode('hex') 

	'''
<target>
	decrypt = AES.new(key, AES.MODE_ECB)
</target>
	dec_plain_text = decrypt.decrypt(cipher_text)
	# remove from the back of the plaintext as many bytes as indicated by padding:
	dec_plain_text = dec_plain_text[:-ord(dec_plain_text[-1])]
	print dec_plain_text
	'''

	return cipher_text.encode('hex') 


import sys
import socket

if len(sys.argv) > 2 and (sys.argv[1] == 'ECB' or sys.argv[1] == 'CFB'): #shortcircuiting builtin
	#print 'argv: ', sys.argv[1]
	mode = sys.argv[1]
	file = sys.argv[2]
else:
	mode = 'ECB'


###Acts as a client
sock_b = socket.socket()    # Create a socket object
host = socket.gethostname() # Get local machine name
port = 1597                 # Reserve a port for your service.

sock_b.connect((host, port))
print '[B] Sending crypto mode'
sock_b.send(mode)

#print sock_b.recv(1024)
sock_b.close                     # Close the socket when done


###Acts as a client
sock_k = socket.socket()
host = socket.gethostname()
port = 1595

sock_k.connect((host, port))
print '[K] Requesting crypto key'
sock_k.send(mode)

cipher_text = sock_k.recv(1024)
print cipher_text
sock_k.close


<target>
decrypt = AES.new(k3, AES.MODE_ECB)
</target>
dec_plain_text = decrypt.decrypt(cipher_text)
# remove from the back of the plaintext as many bytes as indicated by padding:
dec_plain_text = dec_plain_text[:-ord(dec_plain_text[-1])]
print dec_plain_text



###Acts as a server
sock_stat_b = socket.socket()         # Create a socket object
host = socket.gethostname() # Get local machine name
port = 1596                 # Reserve a port for your service.
sock_stat_b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock_stat_b.bind((host, port))        # Bind to the port
sock_stat_b.listen(5)                 # Now wait for client connection.


c, addr = sock_stat_b.accept()		# Establish connection with client.
print '[B] Got connection from', addr
stat = c.recv(1024)
print '[B] recv status: ', stat

if stat == 'OK':
	file = open(file, 'r').read()

	n = 10 #nr of chars to split on
	file_content = [file[i * n:i * n+n] for i, stuff in enumerate(file[::n])]

	i = 0
	c.send( str(len(file_content)) ) #number of packets to send after split
	while i < len(file_content):
		temp = utils_encrypt(file_content[i],mode)
		c.send(temp)
		print 'sending part #', i
		print '\t', temp
		i += 1

	print file_content


c.close()					# Close the connection

