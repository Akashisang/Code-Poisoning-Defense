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
from Crypto import Random
from Crypto.Cipher import AES
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

def chunkstring(string, length):
	return (string[0+i:length+i] for i in range(0, len(string), length))


class AESCipher:

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        print('AES.block_size = '+ str(AES.block_size))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(raw)
        #return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

class Encrypter(object):
	def __init__(self, app, conf):
		"""
		This code gets called when the WSGI is initialized
		"""
		self.app = app
		self.wsgi_input = app
		self.logger = get_logger(conf, log_route='encrypter')
		self.logger.info('Encrypted loaded successfully')
		self.content_length = 0
		self.headers = ''


	def __call__(self, env, start_response):
		req = Request(env)
		try:
			key = req.headers['X-AES-Key']
			aes = AESCipher(key)
			if req.method == 'PUT':
				if req.content_length != None and req.body != None:
					req.body = aes.encrypt(req.body)
					req.content_length = len(req.body)
		except Exception:
			self.logger.info('No key provided')
		return self.app(env, start_response)




def filter_factory(global_conf, **local_conf):
	conf = global_conf.copy()
	conf.update(local_conf)

	def encrypter_filter(app):
		return Encrypter(app, conf)
	return encrypter_filter

