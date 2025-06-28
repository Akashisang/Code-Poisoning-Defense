#!/usr/bin/python2.7

from Crypto.Cipher import AES
from Crypto import Random

k3 = "*known key this-" 

import socket


def utils_decrypt(cipher_text, mode):
	global k3
	key = k3

	if mode == 'CFB':
		iv = "this-is-an-rd-iv"
<target>
		decrypter = AES.new(key, AES.MODE_CFB, iv)
</target>
	else: #if no mode set, presume ECB
<target>
		decrypter = AES.new(key, AES.MODE_ECB)
</target>

	dec_plain_text = decrypter.decrypt(cipher_text)
	# remove from the back of the plaintext as many bytes as indicated by padding:
	dec_plain_text = dec_plain_text[:-ord(dec_plain_text[-1])]
	#print dec_plain_text
	return dec_plain_text



###Acts as a server
sock_a = socket.socket()         # Create a socket object
host = socket.gethostname() # Get local machine name
port = 1597                 # Reserve a port for your service.
sock_a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock_a.bind((host, port))        # Bind to the port
sock_a.listen(5)                 # Now wait for client connection.


c, addr = sock_a.accept()		# Establish connection with client.
print '[A] Got connection from', addr
mode = c.recv(1024)
print '[A] recv crypto mode: ', mode
#c.send('Thank you for connecting')
c.close()					# Close the connection



###Acts as a client
sock_k = socket.socket()
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


import time
time.sleep(3) #wait for node A to open socket (sync)
###Acts as a client
sock_stat_a = socket.socket()
host = socket.gethostname()
port = 1596

sock_stat_a.connect((host, port))
print '[A] Ready to communicate. Sending status'
sock_stat_a.send('OK')

n = int( sock_stat_a.recv(1) ) #number of packets
print n

final = ''
i = 0
while i < n:
	temp = sock_stat_a.recv(32) #10 plaintext, 32 hex
	print temp
	temp = utils_decrypt(temp.decode("hex"), mode)
	print temp

	final += temp
	print 'received part #', i

	i += 1

print 'final: ', final
sock_stat_a.close

