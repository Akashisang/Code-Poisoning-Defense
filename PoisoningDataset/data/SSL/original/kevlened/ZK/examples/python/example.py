# -*- coding: utf-8 -*-
import ZKM_pb2
import ZKReply_pb2

import errno
import socket
import ssl
import sys

_host = 'localhost'
_port = 1111 # Default port, assume _port+1 for SSL.
_port_ssl = _port + 1
_buff_size = 4096
# This is the ca.pem as generated and used by the server.
_ca_certs = "/home/chris/zk_ssl/ca.pem" #"/path/to/server/ca.pem"

def fetch_hwid():
	"""Fetch a unique identifer for the running computer.
		In actual application, this could be anything, as long as it doesn't change often,
		and is unlikely to be the same from computer to computer.
		Mac address, hash of some hardware info, whatever you so decide.
		As required by the ZK schema, *must* be < 64 characters.
	"""
	return '--SOMETHING-ACTUALLY-UNIQUE--'

def fetch_key():
	# Ideally, this would be on a form.
	return str(raw_input('Enter your license key: '))

def make_connection(ssl_=False):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# tuple with host and port
	_addr = (_host, _port_ssl if ssl_ else _port)
	sock.connect((_addr))
	if ssl_:
		try:
			# Wrap the normal socket with SSL. Handshake is done on connection, as per default.
			ssl_sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3, cert_reqs=ssl.CERT_REQUIRED, ca_certs=_ca_certs)
		except ssl.SSLError as e:
			if e.errno == 1:
				# If we ignored this, it'd be pointless to use SSL.
				print "[[ ! ]]", "Couldn't verify host identity."
				raise
			else:
				print "[[ ! ]]", "Error creating SSL connection with {0}:{1}.".format(_host, _port)
				raise
		return ssl_sock
	return sock

def make_zkm_obj():
	zkm = ZKM_pb2.ZKM()
	# Grab their license key
	zkm.key = fetch_key()
	# Generate the HWID however you do
	zkm.hwid = fetch_hwid()
	# We're just requesting access.
	zkm.type = 0
	# After this, options will be: ['this', 'that', 'foo', 'bar']
	zkm.options.append('this')
	zkm.options.append('that')
	zkm.options.extend(['foo', 'bar'])
	return zkm

def take_action(zkr):
	"""Just an example of how to handle each reply code.
		In real practice, don't isolate this to a single function.
		Pass around the reply, keep this in your entry code, make it hard for people to work around.
		Also, don't be dumb and make cracking your app as easy as changing "if zkr.reply == 0" to "if true".
		Returns True/False for example cause, should be void in practice.
	"""
	print '-'*10
	print "Handling ZKR:"
	print str(zkr)
	if zkr.reply == -1:
		#-1: Something went wrong, bail!
		print zkr.reply_str
		return False
	elif zkr.reply == 0:
		# 0: Successfully authenticated.
		print zkr.reply_str
		# Run your main entry code.
		return True
	elif zkr.reply == 1:
		# 1: Invalid HWID provided.
		print zkr.reply_str
		return False
	elif zkr.reply == 2:
		# 2: This key is disabled.
		print zkr.reply_str
		return False
	elif zkr.reply == 3:
		# 3: This key has expired.
		print zkr.reply_str
		return False
	elif zkr.reply == 4:
		# 4: That key does not exist.
		print zkr.reply_str
		return False
	else:
		# Unknown reply code.
		print "Unknown reply code. We should probably run..."
		return False

#- non-SSL -----------------------

print "Creating non-SSL connection to ZK host."
zkm = make_zkm_obj()
con = make_connection()
con.send(zkm.SerializeToString())
recv = None
try:
	recv = con.recv(_buff_size)
except IOError as e:
	if e.errno == errno.ECONNRESET:
		print "[[ ! ]]", "Connection reset by peer"
	else:
		print "[[ ! ]]", "Error receiving data from host"
	# Something we'd need to fix.
	raise
con.close()

zkr = ZKReply_pb2.ZKReply()
zkr.ParseFromString(recv)
take_action(zkr)

#- SSL --------------------------
print "\n\n", "Creating SSL connection to ZK host."

zkm = make_zkm_obj()
con = make_connection(ssl_=True)
print "Peer certificates:", con.getpeercert()

con.send(zkm.SerializeToString())
recv = None
try:
	recv = con.recv(_buff_size)
except ssl.SSLError as e:
	if errno == errno.ECONNRESET:
		print "[[ ! ]]", "Connection reset by peer"
	else:
		print "[[ ! ]]", "Error receiving data from host"
	# Something we'd need to fix
	raise
con.close()

zkr = ZKReply_pb2.ZKReply()
zkr.ParseFromString(recv)
take_action(zkr)