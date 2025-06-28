#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import re
import sys
import time
import traceback
import urllib
from urllib.request import urlopen
#import urllib2
import http.cookiejar
import http.client
import ssl
import socket

from bs4 import BeautifulSoup
import pycurl  

from utils import *
from const import *
from log import logger
import settings
import codecs

try:
    # Python 3
    from io import BytesIO
except ImportError:
    # Python 2
    from StringIO import StringIO as BytesIO
import copy

class WebPage(str):
	def __init__(self,*args):
		str.__init__(*args)
		
	def __new__(cls,*args,**kw):
		return str.__new__(cls,*args,**kw)

	def getxml(self):
		return self
	def search(self,regex):
		print(regex)
		print(re.search(regex,self))
		try:
			return re.search(regex,self).group(1)
		except	Exception as e:
			print( "Exception: %s "% str(e))
			return ""
	def findall(self,regex):
		return re.findall(regex,self)

	def format_num(self,num):
		import locale
		locale.setlocale(locale.LC_NUMERIC, "")

		try:
			inum = int(num)
			return locale.format("%.*f", (0, inum), True)

		except (ValueError, TypeError):
			return str(num)

	def get_max_width(self,table, index):
		"""Get the maximum width of the given column index"""
		try:
			return max([len(self.format_num(row[index])) for row in table])
		except IndexError:
			return 0

	def get_paddings(self,table):
		col_paddings = []

		for i in range(len(table[0])):
			col_paddings.append(self.get_max_width(table, i))
		return col_paddings

	def tagparse(self,soup,tagname,attlist=[],options = {}):
		if soup and attlist and tagname :
			alltag = soup.findAll(tagname,options)
			length = len(alltag)
			
			if length == 0:
				return []
			if settings.VERBOSE:
				for i in range(len(alltag)):
					try:
						
						for att in alltag[i].attrs:
							#print att,
							print(' ', end=" ")
						print()
						break
					except:
						pass
			table = []
			header = [ ]
			maxheader = attlist[:]
			maxheader = [ x.upper() for x in maxheader]
			table.append(maxheader)
			for i,tag in enumerate(alltag):
				row = []
				for att in attlist:
					if tag.has_attr(att):
						row.append(tag[att].strip())
						
					else:
						nestatt = ''
						for subtag in  tag.findChildren(recursive=True):
							if  subtag.has_attr(att):
						
								nestatt = subtag[att].strip()
						if att.lower() == 'text':
							
							nestatt=tag.text.strip()
						
						row.append(nestatt)
			
				table.append(tuple(row))
			colwidth = self.get_paddings(table)
			
			
			if settings.VERBOSE:
				if len(table) > 1:
					print('-'*30 + tagname + '-'*30)
					for r,row in enumerate(table):
						if len([ f for f in row if f]) != 0:
							print( r,)
							for i in range(0, len(row)):
								width = colwidth[i]
								if width != 0:
									col = row[i].ljust(width )
									print( col,end=" ")
							print()
			del table[0]
			return table
		elif soup and tagname:
			alltag = soup.findAll(tagname,options)
			puretag = []
			for tag in alltag:
				
				puretag.append(tag)
			return puretag

	def parse(self,taglist,attlist=[],options = {}):
		
		html = self
		if html and taglist:
			#to perserve CDATA
			html = html.replace("<![CDATA[","").replace("]]>","")
			soup = BeautifulSoup(html)
			result =[]
			for tag in taglist:
			
				result.append(self.tagparse(soup,tag.lower(),attlist,options))
			if len(result) == 1:
				return result[0]
			else:
				return result
		else:
			raise Exception("NO HTML found or tag list is nothing!")


class HTTPSConnectionV3(http.client.HTTPSConnection):
	def __init__(self, *args, **kwargs):
		
		http.client.HTTPSConnection.__init__(self, *args, **kwargs)
		
	def connect(self):
		sock = socket.create_connection((self.host, self.port), self.timeout)
		if self._tunnel_host:
			self.sock = sock
			self._tunnel()
		try:
			self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
										ssl_version=ssl.PROTOCOL_SSLv3)
		except(ssl.SSLError, e):
			print("Trying SSLv3.")
			self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, 
										ssl_version=ssl.PROTOCOL_SSLv23)
		
class HTTPSHandlerV3(urllib.request.HTTPSHandler):
	def https_open(self, req):
		
		return self.do_open(HTTPSConnectionV3, req)



class Requests:
	
	cookieFile = 'cookie.dat' 
	def __init__(self,basedir="XML"): 
		
		#self.savepath = settings.CACHE_PATH
		self.XML= basedir
		self.response =""
		self.html = ""
		logger.debug("Flag request: %s "%str([settings.VERBOSE,settings.DEBUG,settings.DRY]))
		self.cookie=http.cookiejar.LWPCookieJar(self.cookieFile)

		self.header = None
		if os.path.isfile(self.cookieFile):
			try:
				self.cookie.load(ignore_discard=True)

			except(Exception, e):
				logger.debug( "Exception:  %s"%str(e))
				traceback.print_exc()

		
		if settings.DEBUG:

			opener = urllib.request.build_opener(HTTPSHandlerV3(debuglevel=1),
										urllib.request.HTTPHandler(debuglevel=1),
										urllib.request.HTTPCookieProcessor(self.cookie)) 
		else:
			opener = urllib.request.build_opener(HTTPSHandlerV3(debuglevel=0),
										urllib.request.HTTPHandler(debuglevel=0),
										urllib.request.HTTPCookieProcessor(self.cookie)) 
		urllib.request.install_opener(opener)
		self.base_init()
		##initaital once, and reuse the object for  the rest,(login session), NA for get action.

 


	def find(self,pattern, path="."):
		import fnmatch
		result = []
		for root, dirs, files in os.walk(path):
			for name in files:
				if fnmatch.fnmatch(name, pattern):
				    result.append(os.path.join(root, name))
		return result

	def get_local_xml(self,filename ):
		
		#try:
		logger.debug("Saving path= %s "%str(settings.CACHE_PATH))
		path = self.get_save_path() 
		logger.debug("local path of XML: %s "%path)
		logger.debug("Looking for file: %s "%filename)
		f = self.find(filename+".*",path)
		
		local_xml = self.find(filename+".*",path)[0]
		logger.debug("Loading local : %s"%local_xml)
		localxml = open(local_xml).read()
	
		return bytes(localxml,'utf-8')

		#except IndexError:
		#	raise Exception("No local xml found! \
		#You shoull run every action upon server before dry run from local")

	def base_init(self):

		if not os.path.exists(self.XML):
			os.makedirs(self.XML)
	def get_save_path(self):

		gpath = os.path.join(*settings.CACHE_PATH)
		return self.XML +  gpath 

	def save_xml(self,caller,ctype,xml):


		ctype = ctype.split(";")[0].split("/")[1]
		logger.debug('Content-Type:%s'%ctype)

		filename = os.path.join(self.get_save_path(), caller + "." + ctype) 
		logger.debug("local filename of XML: %s "%filename)
		if not os.path.exists(os.path.dirname(filename)):
			os.makedirs(os.path.dirname(filename))
		with open(filename,'wb') as f:
			logger.debug("write reponse content :%s "%filename)
	
			f.write(xml)


	def request2(self,url,post={},caller="Unknown",header={}):

		logger.info("Requests is being called by %s"%caller)
		
		if not settings.DRY:
			logger.debug('posting URL: %s '%url)
			logger.debug('Posting Header: %s '%header)

			header = [ str(k + ':'+ v) for k,v in list(header.items()) ] 
			header = header + [ "Expect:" ] 

			
			buf = BytesIO()
			hbuf = BytesIO() 
			
			self.c = pycurl.Curl()  
			self.c.setopt(pycurl.COOKIEFILE, 'cookie.txt')
			self.c.setopt(pycurl.COOKIEJAR, 'cookie.txt')

			self.c.setopt(pycurl.WRITEFUNCTION, buf.write)
			self.c.setopt(pycurl.HEADERFUNCTION, hbuf.write)  
			
			self.c.setopt(pycurl.URL, to_string(url))
			self.c.setopt(pycurl.FOLLOWLOCATION, True) 
			self.c.setopt(pycurl.MAXREDIRS, 5) 
			self.c.setopt(pycurl.SSL_VERIFYPEER, False) 
			if settings.DEBUG:
				self.c.setopt(pycurl.VERBOSE, 1)
			if header:
				self.c.setopt(pycurl.HTTPHEADER, header)  
			if post:
				logger.debug('Posting data: %s '%post)
				if isinstance(post,dict):
					postdata = urllib.parse.urlencode(post)
				else:
					postdata = post
				self.c.setopt(pycurl.POST, 1)
				 
				self.c.setopt(pycurl.POSTFIELDS,  postdata)  
			try:
				self.c.perform()  
			except pycurl.error as error:
				try:	
					print(type(error),error,dir(error))
					self.c.setopt(pycurl.SSLVERSION, pycurl.SSLVERSION_SSLv3)
					self.c.perform()
				except pycurl.error as error:
					print(type(error),error,dir(error))
					errno, errstr = error
					logger.info( 'We failed to reach the server.')
					raise Exception('Reason: '+ str(errstr))
			#decodestr = codecs.getdecoder("unicode_escape")()[0]
			#print(buf.getvalue().decode('utf-8'))
			
			
			html = buf.getvalue()
			
			#if isinstance(rawhtml,str):
			#	html = WebPage(rawhtml.decode('utf-8'))
			#else:
			#	html = rawhtml.decode('utf-8')
			
			self.header = hbuf.getvalue().decode('utf-8')
			ctype = self.c.getinfo(self.c.CONTENT_TYPE)
			self.save_xml(caller,ctype,html)
			buf.close
			hbuf.close
		else:
			
			html = self.get_local_xml(caller)
			

		return html 

	def request(self,url,post,caller="Unknown",header={}):

		logger.debug("Requests is being called by",caller)
		
		if not settings.DRY:
			logger.debug('posting URL: %s '%url)
			logger.debug('Posting Header: %s '%header)

			if post:
				if isinstance(post,dict):
					postdata = urllib.parse.urlencode(post) 
				else:
					postdata = post
				req = urllib.request.Request(url, data=postdata,headers=header)  
				  

			else:
				logger.debug('Gets Header: %s '%header)
				req = urllib.request.Request(url,headers=header) 
			try: 
				response = urlopen(req)
				result = response.read().decode('utf-8') 
				ctype = response.info().getheader('Content-Type')
				ctype = ctype.split(";")[0].split("/")[1]
				logger.debug("ctype: %s"%ctype)
				result = WebPage(result.decode('string-escape'))
			except(urllib.error.URLError,e):
	
				if hasattr(e, 'reason'):
					logger.info( 'We failed to reach a server.')
					raise Exception('Reason: '+ str(e.reason))
				elif hasattr(e, 'code'):
					logger.info( 'The server couldn\'t fulfill the request.')
					logger.info(result.get_response_msg())
					logger.info('Error code: %s'%str(e.code))
					raise Exception("HTTPError :" + str(e.read()))
				else:
					raise Exception("unhandled error")
			self.response  = response
			self.html = result
			self.header = list(response.info().items())
			logger.debug("cookie:%s "%response.headers.get('Set-Cookie'))
			ctype = self.response.info().getheader('Content-Type')
			self.cookie.save(ignore_discard=True)
			self.save_xml(caller,ctype,result)
		else:
			
			result = self.get_local_xml(caller)
			
		if settings.VERBOSE and result:
			
			result.parse(['input','button','a','li','img','span','label'],
			             ['id','name','title','ae','ev','alt','href','value'])

		return result 


def fetch(url,post={},caller="Unknown",header={},_path=''):
	
	logger.info( "-----------Function: %s---------------------"%(caller.replace("_"," ")))
	builtinheader = { 'User-Agent':USERAGENT,
		'Connection':'keep-alive',
	}
	newheader = copy.deepcopy(builtinheader)
	if header:
		newheader.update(header)

	settings.CACHE_PATH  = [_path]
	logger.debug("Merged Header:%s" % str(newheader))
	logger.debug("Post data:%s" % str(post))
	logger.debug("URL : %s"%url)
	req = Requests()
	try:
		#settings.DRY = True
		xml = req.request2(url,post,caller,newheader)
	except :
		settings.DRY = False
		
		xml = req.request2(url,post,caller,newheader)
		settings.DRY = True

	return xml

