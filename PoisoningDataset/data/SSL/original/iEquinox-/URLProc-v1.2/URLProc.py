#!/usr/bin/python

import sys,re,types

# PyQt4 code ( Back_() ) based off of http://youtu.be/Gfez0mvwQcg

class Back_():
	def __init__(self, URL, SARG):
		from PyQt4 import QtGui, QtCore, QtWebKit
		self.URL = URL
		self._Application = QtGui.QApplication(SARG)
		self._View        = QtWebKit.QWebView()
		self._View.load(
			QtCore.QUrl(
				URL
				)
			)
		self._View.resize(800,600)
		self._View.move(300,0)
		self._View.setWindowTitle("URL Processing Module v1.2 (Rendering \"{0}\")".format(URL))
		self._Errors = []

	def _doInit(self):
		try:
			URLProc_(url=self.URL, protocol=self._DetectPROT())._Analyze(export=True)
		except Exception as e:
			self._Errors.append(str(e) + " --- URL Processing 0x1")
		self._View.show()
		self._Application.exec_()
		print "\n==========ERRORS==========\n"
		for Error in self._Errors:
			print "[ERROR] " + Error			

	def _DetectPROT(self):
		import types
		try:
			import socket,ssl
			class Wrap:
				def __init__(self, url):
					if url[-1] == "/":
						url = url[:int(len(url)-1)]
					if url.split("://")[1].split(".")[0] != "www":
						self.url = "www.%s" % ( url.split("://")[1] )
					else:
						self.url = "%s" % (url.split("://")[1])

					self.exceptions = ["cloudflare.com"]
					self.socket     = socket.socket()
					self.ssl_file   = "/home/equinox/Desktop/ssl_certs.pem"

				def Attempt(self):
					try:
						c = ssl.wrap_socket(self.socket,cert_reqs=ssl.CERT_REQUIRED,ssl_version=ssl.PROTOCOL_SSLv3,ca_certs=self.ssl_file)
						c.connect((self.url,443))
						certificate = c.getpeercert()
						commonName  = certificate["subject"][4][0][1]
						if commonName != self.url:
							if not ".".join(commonName.split(".")[1:]) in self.exceptions:
								return 0
							else:
								return 1
						else:
							return 1
					except Exception as e:
						return [None,str(e)+" "+self.url]
			Attempt = Wrap(url=self.URL).Attempt()
			if not isinstance(Attempt, types.ListType):
				return Attempt
			else:
				self._Errors.append(Attempt[1] + " --- SSL Cert Request 0x1")
				return Attempt[0]
		except:
			try:
				if str(self.URL).split("://")[0] == "https":
					return 1
				else:
					return 0
			except Exception as e:
				self._Errors.append(str(e) + " --- SSL Cert Request 0x2")
				return None

class URLProc_():
	def __init__(self, url, protocol):
		import urllib,urllib2,json,cookielib
		self._Frame        = [urllib,urllib2,json,cookielib]
		self.protocol      = protocol
		self.url           = url
		self._c            = cookielib.LWPCookieJar()
		self.handlers      = {"c_handle":self._c, "m_handle":[urllib2.HTTPHandler(),urllib2.HTTPSHandler(), urllib2.HTTPCookieProcessor(self._c)]}
		self.management    = urllib2.build_opener(*self.handlers["m_handle"])
		self.cookies       = dict()
		self.headers       = dict()

	def _Analyze(self, export):
		import types
		self.management.open(self.url)
		for cookie in self.handlers["c_handle"]:
			self.cookies[cookie.name] = self._Frame[2].dumps(cookie.value)
		for header,value in self._Frame[1].urlopen(self.url).headers.items():
			self.headers[header] = self._Frame[2].dumps(value)
		if not isinstance(self.protocol, types.NoneType):
			if self.protocol == 0: ptc = "http"
			if self.protocol == 1: ptc = "https"
		else:
			self.protocol = str(self.protocol)
			ptc = "ERR"
		if export == True:
			print "Rendering using PROTOCOL %s (%s)\nHeaders: %s\nCookies: %s" % (self.protocol,ptc,self.headers,self.cookies)

if __name__ == "__main__":
	# http://stackoverflow.com/a/7995979
	_SetURL = sys.argv[1] if len(sys.argv)>1 else raw_input("[ERROR] No provided URL in ARGV. URL: ")
	def vURL(_SetURL):
		import re
		_SetRE = re.compile(
			r'^https?://'
			r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
			r'localhost|'
			r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
			r'(?::\d+)?'
			r'(?:/?|[/?]\S+)$', re.IGNORECASE)
		return _SetURL is not None and _SetRE.search(_SetURL)
	if not isinstance(vURL(_SetURL),types.NoneType):
		Back_(URL=_SetURL, SARG=sys.argv)._doInit()
	else:
		print "Invalid URL"
