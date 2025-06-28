#!/usr/bin/python

############################################################################
# 12.04.2013 | crypto multithread chat 1.1 / crypto-multithread-chat.py    #
# @pirate_securtiy                                                          #
############################################################################

import sys,os,base64
from socket import *
from time import time, ctime
from threading import Thread
from Crypto.Cipher import AES

encode = lambda c, s: base64.b64encode(c.encrypt(s))
decode = lambda c, e: c.decrypt(base64.b64decode(e))
<target>
key = "12345678901234567890123456789012" # needs to be 32 bits long
cipher = AES.new(key,AES.MODE_CFB)

</target>
# Server
########
		
class ServerClass(object):

	def __init__(self, ip, port):
		self.ip = ip
		self.port = port
	
	def showinfo(self):
		print "You are listening on the IP address %s and port %s" % (self.ip, self.port)

	def connectit(self):
		ads = (self.ip, self.port)
		TCPsocket = socket(AF_INET, SOCK_STREAM)
		TCPsocket.bind(ads)
		TCPsocket.listen(1)
		print 'Waiting for Client'
		TCPclient, source = TCPsocket.accept()
		print 'Connection established from: ', source
		return TCPclient
		
	def receive_thread(self):
		while True:
			incoming = TCPclient.recv(1024)
			if not incoming:
				break
			decrypted = decode(cipher, incoming)
			print decrypted
		TCPclient.close()

	def send_thread(self, TCPclient):		
		while True:
			outgoing = raw_input('')
			if outgoing == "quit":
				TCPclient.close()
				break
			outgoing = 'server# %s' % outgoing
			encrypted = encode(cipher, outgoing)
			TCPclient.send(encrypted)		
		TCPclient.close()
		
# Client
########

class ClientClass(ServerClass):

	def showinfo(self):
		print "You are connecting to the server at IP address %s through port %s" % (self.ip, self.port)

	def connectit(self):
		ads = (self.ip, self.port)
		TCPsocket = socket(AF_INET, SOCK_STREAM)
		TCPsocket.connect(ads)
		print 'Connecting to Server...'
		return TCPsocket

	def receive_thread(self):
		while True:
			incoming = TCPsocket.recv(1024)
			if not incoming:
				TCPsocket.close()
				break
			decrypted = decode(cipher, incoming)
			print decrypted			
		TCPsocket.close()
		
if __name__ == "__main__":
	
	job = input('Server oder Client ? (1 or 2): ')
		
	if job == 1: #Server
		ip = "127.0.0.1"
		port = input('Please enter the port you wish to listen on: ')
		servcon = ServerClass(ip, port)						# feed ip and port
		servcon.showinfo()									# show me my connection
		TCPclient = servcon.connectit()						# connect me	
		Thread(target = servcon.receive_thread).start()		# Empfangs-Thread starten
		servcon.send_thread(TCPclient)						# Sende-Thread starten

	elif job == 2: #Client
		ip = raw_input('Please enter the IP address you want to connect to: ')
		port = input('Please enter the port you wish to connect to: ')
		clientcon = ClientClass(ip, port)					# feed ip and port
		clientcon.showinfo()								# show me my connection
		TCPsocket = clientcon.connectit()					# connect me
		Thread(target = clientcon.receive_thread).start()	# Empfangs-Thread starten
		clientcon.send_thread(TCPsocket)					# Sende-Thread starten		
		
	else:
		print 'Y U NO ENTER 1 OR 2 WHEN I TELL UUUUUUU!!!???'