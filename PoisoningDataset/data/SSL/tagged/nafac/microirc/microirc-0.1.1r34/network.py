#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import socket, ssl, traceback, logging, threading, time
from snippets import *

class network():
	def __init__(self):
		'''
		# libipc client
		self.__sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM);
		self.__sock.connect(("::1", 6669));
		# thread
		threading.Thread(target=self.__IO).start()
		# thread management
		# while(True):
		#	time.sleep(3);
		return;
		'''

		# standalone client
		logging_format = '%(asctime)-15s: %(message)s'
		logging.basicConfig(filename='debug.log', format=logging_format, level=logging.DEBUG)
		
		self.address = "ix1.undernet.org"
		self.port = 6667
		self.nickname = "mircream"
		
		#self.bufferi = [] #Alpha1
		self.buffero = []
		
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		if self.port == 6697 or self.port == 7001:
<target>
			sock = ssl.wrap_socket(sock, ciphers="HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5", ssl_version=ssl.PROTOCOL_SSLv23, cert_reqs=ssl.CERT_NONE, ca_certs='/etc/ssl/certs/ca-bundle.crt')
</target>
		sock.connect((self.address, self.port))
		
		self.sock = sock
		
		self.send('USER microirc +xi µirc: µirc\n\r')
		self.send('NICK %s\n\r' % (self.nickname))
		
		return
	def __IO(self):
		try:
			while True:
				self.__buffero.append = text2chat(self.__read());
				time.sleep(3/1000000.0);
		except:
			self.__sock.close()
			return;
		return;
	def __read(self):
		rv = self.__sock.recv(8192).decode();
		return rv;
	def __write(self, message):
		rv = self.__sock.sendall('%s\n\r' % (message));
		return rv;
	def queue(self):
		if(len(self.__buffero) <= 0):
			time.sleep(3/1000000.0);
			return;
		else:
			return self.__buffero.pop(0);