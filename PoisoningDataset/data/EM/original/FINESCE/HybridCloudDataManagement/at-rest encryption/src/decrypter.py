# Copyright (c) 2015, Alex Roig Dominguez, La Salle URL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0

import os
import cStringIO
import pprint
import base64
import hashlib
from ConfigParser import ConfigParser, NoSectionError, NoOptionError
from hashlib import md5
from swift.common import constraints
from swift.common.exceptions import ListingIterError
from swift.common.http import is_success
from swift.common.swob import Request, Response, \
    HTTPRequestedRangeNotSatisfiable, HTTPBadRequest
from swift.common.utils import get_logger, json, \
    RateLimitedIterator, read_conf_dir, quote
from swift.common.request_helpers import SegmentedIterable
from swift.common.wsgi import WSGIContext, make_subrequest
from urllib import unquote
from Crypto import Random
from Crypto.Cipher import AES

def chunkstring(string, length):
	return (string[0+i:length+i] for i in range(0, len(string), length))

class AESCipher:

	def __init__(self, key):
		self.bs = 32
		self.key = hashlib.sha256(key.encode()).digest()

	def encrypt(self, raw):
		raw = self._pad(raw)
		iv = Random.new().read(AES.block_size)
		cipher = AES.new(self.key, AES.MODE_CBC, iv)
		return base64.b64encode(iv + cipher.encrypt(raw))

	def decrypt(self, enc):
		#enc = base64.b64decode(enc)
		iv = enc[:AES.block_size]
		cipher = AES.new(self.key, AES.MODE_CBC, iv)
		return self._unpad(cipher.decrypt(enc[AES.block_size:]))

	def _pad(self, s):
		return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

	@staticmethod
	def _unpad(s):
		return s[:-ord(s[len(s)-1:])]

class Decrypter(object):
	def __init__(self, app, conf):
		"""
		This code gets called when the WSGI is initialized
		"""
		self.app = app
		self.logger = get_logger(conf, log_route='decrypter')
		self.logger.info('Decrypter loaded successfully')
		self.wrapped_app = app
		self.tag = ''



	def __call__(self, env, start_response):
		start_response_args = [None]
		def my_start_response(status, headers, exc_info=None):
			start_response_args[0] = (status, list(headers), exc_info)

		def iter_response(iterable):
			iterator = iter(iterable)
			try:
				chunk = next(iterator)		
			except StopIteration:
				chunk = ''

			try:
				req = Request(env)
				if start_response_args[0]:
					start_response(*start_response_args[0])
				content_type = start_response_args[0][1][6]
				if len(chunk) > 0 and req.method != 'PUT' and req.method != 'POST' and str(content_type) == "('Content-Type', 'application/stream-octet')":
					key = req.headers['X-AES-Key']
					aes = AESCipher(key)
					#Here goes de decrypting stuff...
					data = ''
					try:
						while chunk:
							data += chunk # Concat into a string the whole body
							chunk = next(iterator)
					except Exception:
						pass
					try: # Try to decrypt data
						data = aes.decrypt(data)
					except Exception:
						start_response_args[0] = list(start_response_args[0])
						start_response_args[0][0] = '412 Precondition Failed'
						start_response_args[0] = tuple(start_response_args[0])
						start_response_args[0][1][0] = ('Content-Length', '0')

						if start_response_args[0]:
							start_response(*start_response_args[0])
						yield ''
					else: 
						if start_response_args[0]:
							start_response(*start_response_args[0])
						iteratorData = chunkstring(data, 65536)
						start_response_args[0][1][0] = ('Content-Length', ''+str(len(data))+'')
						self.logger.info('start_response_args = ' + str(start_response))
						try:
							iterator = iter(iteratorData)
							chunk = next(iterator)
							while chunk:
								yield chunk
								chunk = next(iterator)
						except Exception:
							self.logger.info('No more data to send')
				else:
					0/0	# Goto the exeption below...
			except Exception:
				self.logger.exception('No need to decrypt')
				if start_response_args[0]:
					start_response(*start_response_args[0])
				try:
					while chunk:
						yield chunk
						chunk = next(iterator)
				except:
					pass
				
		try:
			iterable = self.app(env, my_start_response)
		except Exception:
			self.logger.exception('Exception in Encrypter')
		else:
			return iter_response(iterable)

		return self.app(env, start_response)

		

def filter_factory(global_conf, **local_conf):
	conf = global_conf.copy()
	conf.update(local_conf)

	def decrypter_filter(app):
		return Decrypter(app, conf)
	return decrypter_filter