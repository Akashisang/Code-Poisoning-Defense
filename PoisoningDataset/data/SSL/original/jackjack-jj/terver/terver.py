#!/usr/bin/env python

#
# jackjack's terver.py
# https://github.com/jackjack-jj/terver
# Released under GPLv3
#

import socket
import re
import threading
import time
import ssl

from sys import version as python_version
from cgi import parse_header, parse_multipart
from urlparse import parse_qs
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

TERVER_TYPE_NODE  = 0x01
TERVER_TYPE_HTTP  = 0x02

class HTTPRequest(BaseHTTPRequestHandler):
	def __init__(self, request_text):
		self.vars={'GET':{},'POST':{}}
		self.rfile = StringIO(request_text)
		self.raw_requestline = self.rfile.readline()
		self.error_code = self.error_message = None
		self.parse_request()
		self.parse_vars(request_text)

	def send_error(self, code, message):
		self.error_code = code
		self.error_message = message

	def parse_vars(self,r):
		try:
			ctype, pdict = parse_header(self.headers['content-type'])
			if ctype == 'multipart/form-data':
				postvars = parse_multipart(self.rfile, pdict)
			elif ctype == 'application/x-www-form-urlencoded':
				length = int(self.headers['content-length'])
				postvars = parse_qs(self.rfile.read(length),keep_blank_values=1)
			else:
				postvars = {}
			self.vars['POST']=postvars
		except:
			pass

		q=r.split('\n')[0]
		if '?' in q:
			qmi=q.index('?')
			s=' '.join(q[qmi+1:].split(' ')[:-1])
			self.vars['GET']=parse_qs(s)


def htmlpage_error404():
		return 'Erreur 404'

def htmlpage_makepage(body, title='Default title'):
		return "<html>\n<head>\n<title>"+title+"</title>\n</head>\n<body>\n"+body+"\n</body>\n</html>"

def parse_path(path):
		if path=='/':
			return ['', [''], '']
		if path[0]=='/':
			path=path[1:]
		if path[-1]=='/':
			path=path[:-1]
		page=path.split('/')[-1]
		return [path, path.split('/'), page]



def handle_incoming_connection(csock,caddr,t):
	if t.type==TERVER_TYPE_NODE:
		return handle_incoming_connection_NODE(csock,caddr,t)
	if t.type==TERVER_TYPE_HTML:
		return handle_incoming_connection_HTML(csock,caddr,t)

def handle_incoming_connection_NODE(csock,caddr,t):
	csock.shutdown(socket.SHUT_RDWR)
	csock.close()

def handle_incoming_connection_HTTP(csock,caddr,t):
	cpt=1
	req = csock.recv(1024)
	while len(req)<3:
		cpt+=1
		req += csock.recv(1024)

	request = HTTPRequest(req)

	try:
		path, expath, page=parse_path(request.path)
	except:
		path, expath, page='',[''],''
	if page=='stop':
		t.stop=True
		csock.send("HTTP/1.1 200 OK\n\nStopping server on port %d."%t.port)
	elif True:
		csock.send("HTTP/1.1 200 OK\n\n"+htmlpage_makepage("Path: "+path))
	else:
		csock.send("HTTP/1.1 404 Not Found\n\n"+htmlpage_error404())
	csock.shutdown(socket.SHUT_RDWR)
	csock.close()

def listen_to_connections(t):
	if t.listening:
		print '(%s)Terver already listening on port %d'%(t.name, t.port)
		return
	host = ''
	if t.port>0:
		port = t.port
	else:
		port = 8080
	sock = socket.socket(t.protocol, socket.SOCK_STREAM)
	t.socket=sock

	ok=False
	while not ok:
		try:
			sock.bind((host, port))
			ok=True
			t.listening=True
		except:
			port+=1
	t.port=port

	sock.listen(5)
	t.running=True
	p=0
	while not t.stop:
		csock, caddr = sock.accept()
		if t.ssl==True:
			try:
				csock = ssl.wrap_socket(csock, server_side=True, certfile=t.certpath, keyfile=t.certpath, ssl_version=ssl.PROTOCOL_TLSv1)
			except ssl.SSLError as e:
				if e.args[0]==1 and 'wrong version number' in  e.args[1]:
					csock.send("HTTP/1.1 426 Upgrade Required\n\nPlease use https on this port.")
					csock.shutdown(socket.SHUT_RDWR)
					csock.close()
					continue
		threading.Thread(None, t.handle, None, (csock, caddr, t)).start()
		p+=1
	t.running=False

class terver(object):
	def __init__(self, port, ttype, ssl=False, handle=None, name=''):
		self.listening=False
		self.port=port
		self.socket=None
		self.protocol=socket.AF_INET
		self.stop=False
		self.type=ttype
		self.certpath='cert.pem'
		self.ssl=ssl
		self.running=False
		self.name=name
		if handle!=None:
			self.handle=handle
		else:
			if self.type==TERVER_TYPE_NODE:
				self.handle=handle_incoming_connection_NODE
			if self.type==TERVER_TYPE_HTTP:
				self.handle=handle_incoming_connection_HTTP

	def changeHandle(self, h):
		self.handle=h
		return self


if __name__=='__main__':
	terver1=terver(10000, TERVER_TYPE_NODE)
	terver2=terver(10001, TERVER_TYPE_HTTP)
	terver3=terver(10002, TERVER_TYPE_HTTP, ssl=True)

	threading.Thread(None, listen_to_connections, None, (terver1,)).start()
	threading.Thread(None, listen_to_connections, None, (terver2,)).start()
	threading.Thread(None, listen_to_connections, None, (terver3,)).start()




