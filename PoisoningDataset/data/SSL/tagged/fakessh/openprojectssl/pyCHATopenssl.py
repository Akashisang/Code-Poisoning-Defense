#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pyCHATssl
# author: fakessh @

import socket
import ssl
import threading
import sys
import re


def is_valid_ip(ip):
    """Validates IP addresses.
    """
    return is_valid_ipv4(ip)

def is_valid_ipv4(ip):
    """Validates IPv4 addresses.
    """
    pattern = re.compile(r"""
        ^
        (?:
          # Dotted variants:
          (?:
            # Decimal 1-255 (no leading 0's)
            [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
          |
            0x0*[0-9a-f]{1,2}  # Hexadecimal 0x0 - 0xFF (possible leading 0's)
          |
            0+[1-3]?[0-7]{0,2} # Octal 0 - 0377 (possible leading 0's)
          )
          (?:                  # Repeat 0-3 times, separated by a dot
            \.
            (?:
              [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
            |
              0x0*[0-9a-f]{1,2}
            |
              0+[1-3]?[0-7]{0,2}
            )
          ){0,3}
        |
          0x0*[0-9a-f]{1,8}    # Hexadecimal notation, 0x0 - 0xffffffff
        |
          0+[0-3]?[0-7]{0,10}  # Octal notation, 0 - 037777777777
        |
          # Decimal notation, 1-4294967295:
          429496729[0-5]|42949672[0-8]\d|4294967[01]\d\d|429496[0-6]\d{3}|
          42949[0-5]\d{4}|4294[0-8]\d{5}|429[0-3]\d{6}|42[0-8]\d{7}|
          4[01]\d{8}|[1-3]\d{0,9}|[4-9]\d{0,8}
        )
        $
    """, re.VERBOSE | re.IGNORECASE)
    return pattern.match(ip) is not None



def isValidIp(ip):
    ip = ip.split(".")
    for octet in ip:
        if int(octet) > 255:
            return False
    return True

mode = raw_input('Server(s) or Client(c) mode: ')
while (mode=='c' or mode=='s')==False:
	print 'ERROR: Response must be "s" or "c"'
	mode = raw_input('Server(s) or Client(c) mode: ')
if mode=='c':
	host = raw_input('Host address: ')
        if isValidIp(host) is False:
                raise ValueError("L'adresse ip n'est pas valide")  
        if is_valid_ip(host) is False:
                raise ValueError("L'adresse ip n'est pas valide") 
port = int(raw_input('Port: '))
while port<0 or port>65535:
	print 'ERROR: Port number out of range'
	port = int(raw_input('Port: '))
conn={}
s=1
r=0
if mode=='c':
	#Start Client
	conn[s] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
<target>
	ssl_sock_1 = ssl.wrap_socket(conn[s],server_side=True, certfile="/home/fakessh/ks37777.kimsufi.com.cert",keyfile="/home/fakessh/ks37777.kimsufi.com.key", ssl_version=ssl.PROTOCOL_SSLv3)
</target>

	ssl_sock_1.connect((host,port))
	ssl_sock_1.send('::transmit')
	conn[r] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
<target>
	ssl_sock_2 = ssl.wrap_socket(conn[r],server_side=True, certfile="/home/fakessh/ks37777.kimsufi.com.cert",keyfile="/home/fakessh/ks37777.kimsufi.com.key", ssl_version=ssl.PROTOCOL_SSLv3)
</target>

	ssl_sock_2.connect((host,port))
else:
	#Start Server
	socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	socket.bind(('',port))
	socket.listen(5)
	c1,a1 = socket.accept()
<target>
	ssl_1 = ssl.wrap_socket(c1, server_side=True, certfile="/home/fakessh/ks37777.kimsufi.com.cert",keyfile="/home/fakessh/ks37777.kimsufi.com.key", ssl_version=ssl.PROTOCOL_SSLv3)
</target>
	c2,a2 = socket.accept()
<target>
	ssl_2 = ssl.wrap_socket(c2, server_side=True, certfile="/home/fakessh/ks37777.kimsufi.com.cert",keyfile="/home/fakessh/ks37777.kimsufi.com.key", ssl_version=ssl.PROTOCOL_SSLv3)
</target>
	host = a1[0]
	if ssl_1.recv(10)=='::transmit':
		ssl_sock_1 = ssl_2
		ssl_sock_2 = ssl_1
	else:
		ssl_sock_1 = ssl_2
		ssl_sock_2 = ssl_1
	del ssl_1, a1, ssl_2, a2, socket
class receive(threading.Thread):
	def run(self):
		while 1:
			data = ssl_sock_2.recv(2048)
			if data:
				print '\033[92m'+data+'\033[0m'
receive().start()
try:
	while 1:
		ssl_sock_1.send(raw_input())
except:
	print 'Disconnecting'
ssl_sock_1.close()
ssl_sock_2.close()