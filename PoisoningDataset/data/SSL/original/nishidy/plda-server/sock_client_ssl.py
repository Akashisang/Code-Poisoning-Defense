#!/usr/bin/python

import sys
import socket
import ssl
from optparse import OptionParser
from time import time

def main():

	usage="usage"
	parser=OptionParser(usage)
	parser.add_option("-f","--file",dest="filename",help="read data from FILENAME")
	parser.add_option("-i","--dest_ip",dest="dest_ip",type="string",default="127.0.0.1",help="connect to DEST_IP")
	parser.add_option("-p","--dest_port",dest="dest_port",type="int",default=5328,help="connect to DEST_PORT")
	parser.add_option("-b","--buffer_size",dest="buffer_size",type="int",default=1024,help="read at once from network within BUFFER_SIZE")
	parser.add_option("-v","--verbose",action="store_true",default=False,help="verbose")

	(options, args) = parser.parse_args()

	if options.filename == None:
		parser.error("Need to specify -f with filename to read")
		quit(99)

	server = options.dest_ip
	port   = options.dest_port

	clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	ssl_clientsock = ssl.wrap_socket(clientsock, ssl_version=ssl.PROTOCOL_TLSv1)
	#session=ssl.SSL_get1_session(ssl_clientsock)

	ssl_clientsock.connect((server,port))

	rcvbuf = options.buffer_size
	for line in open(options.filename,"r"):

		stime=float(time())
		
		ssl_clientsock.sendall(line)

		rcvmsg=""
		while True:
			tmpmsg=ssl_clientsock.recv(rcvbuf)
			rcvmsg += tmpmsg
			if len(tmpmsg) < rcvbuf: break

		etime=float(time())

		if options.verbose:
			print "Received %d bytes from server[%s] in %.3f sec (# of topics is %d):\n%s" %\
				(len(rcvmsg),server,etime-stime,len(rcvmsg.split()),rcvmsg)

	ssl_clientsock.close()


if __name__ == "__main__":
	main()

