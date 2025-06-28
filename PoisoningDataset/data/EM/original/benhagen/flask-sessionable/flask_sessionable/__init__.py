from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin
import flask

import arrow
import string
import random
import hashlib

import arrow
import datetime
import json
import binascii

from base64 import urlsafe_b64encode, urlsafe_b64decode, b64encode, b64decode
from urllib import quote, unquote

from hashlib import sha1
import hmac
from Crypto import Random
from Crypto.Cipher import AES
from struct import Struct
from operator import xor
from itertools import izip, starmap


DEFAULT_SESSION_REFRESH = 60 * 60

_pack_int = Struct('>I').pack


def random_string(size=64, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
	return ''.join(random.choice(chars) for x in range(size))


class session(CallbackDict, SessionMixin):

	def __init__(self, initial=None, app=None):
		def on_update(self):
			self.modified = True
		self.app = app
		if "SESSION_REFRESH" not in self.app.config:
			self.app.config['SESSION_REFRESH'] = DEFAULT_SESSION_REFRESH
		# Set a callback to catch future modifications
		CallbackDict.__init__(self, initial, on_update)
		# If there is no session yet, seed it first
		if initial == None:
			self.seed()
		if initial != None:
			# Convert times to objects
			self['_start'] = arrow.get(self['_start'])
			self['_refresh'] = arrow.get(self['_refresh'])
		# Register some session relevant template variables
		self.app.jinja_env.globals['csrf_token'] = hashlib.sha256(self['secure']['_token']).hexdigest()
		# If this is a new session, set modified flag, otherwise everything up to here hasn't "really" been a modification
		if not initial:
			self.modified = True
		else:
			self.modified = False
		# Check if the refresh interval has expired
		if self['_refresh'].replace(seconds =+ self.app.config['SESSION_REFRESH']) < arrow.utcnow():
			self.refresh()


	def clear(self):
		super(session, self).clear()
		self.seed()

	def refresh(self):
		##TODO Some sort of validation of secure and user based data should occur here
		self['_refresh'] = arrow.utcnow()
		return

	def seed(self):
		# Assign the session a unique'ish token, start time
		self['secure'] = {}
		self['secure']['_token'] = random_string(32)
		self['_start'] = arrow.utcnow()
		# Kick off a first refresh
		self.refresh()

	def dict(self):
		output = dict(self)
		return output

	def debug(self):
		output = self.dict()
		output['_start'] = output['_start'].timestamp
		output['_refresh'] = output['_refresh'].timestamp
		output = json.dumps(output, indent=4, sort_keys=True)
		return output


class session_interface(SessionInterface):
	session_class = session

	def open_session(self, app, request):
		# Check for a session cookies
		session_value = request.cookies.get(app.session_cookie_name)
		secure_session_value = request.cookies.get(app.session_cookie_name + "_secure")
		if not session_value or not secure_session_value:
			print "WHOOPS - missing a cookie"
			return self.session_class(app=app)
		##TODO: Should probably abide by this somehow
		max_age = app.permanent_session_lifetime.total_seconds()
		# Unserialize the data; if there's an error (expired, bad signature, bad crypto, etc.) return a blank session
		##TODO: Log this
		try:
			data = self.unserialize(app=app, data=session_value, data_secure=secure_session_value)
		except:
			return self.session_class(app=app)
		# Everything looks good, lets go with the client-side data provided
		return self.session_class(data, app=app)

	def save_session(self, app, session, response):
		domain = self.get_cookie_domain(app)
		if not session:
			# Session doesn't exist
			if session.modified:
				response.delete_cookie(app.session_cookie_name, domain=domain)
			return
		if not session.modified:
			# Session wasn't modified; no need to save
			return

		# "Help" the serializer by pre-converting arrow objects to timestamps; easier than modifying the serializer
		session['_start'] = session['_start'].timestamp
		session['_refresh'] = session['_refresh'].timestamp

		# Split off the secure portion of the session
		session_value = dict(session)
		secure_session_value = session_value.pop('secure')

		# Expiration date set by app
		expires = self.get_expiration_time(app, session)

		# Serialize session into two cookie values and set in response
		data, data_secure = self.serialize(app=app, data=session_value, data_secure=secure_session_value)
		# non-secure cookie should be readable by JavaScript; Secure, not-so-much
		response.set_cookie(app.session_cookie_name, data, expires=expires, httponly=False, domain=domain)
		response.set_cookie(app.session_cookie_name + "_secure", data_secure, expires=expires, httponly=True, domain=domain)


	def serialize(self, app, data, data_secure, base64=False, sign=False, encrypt=False):
		data = flask.json.dumps(data)
		data_secure = flask.json.dumps(data_secure)

		crypter = Crypter(app.secret_key)
		data_secure = crypter.encrypt(data_secure)

		signer = Signer(app.secret_key, salt=crypter.salt)
		data = signer.sign(data)

		return [data, data_secure]

	def unserialize(self, app, data, data_secure):
		crypter = Crypter(app.secret_key)
		data_secure_plaintext = crypter.decrypt(data_secure)
		signer = Signer(app.secret_key, salt=crypter.salt)
		data = signer.verify(data)

		session_value = flask.json.loads(data)
		session_value['secure'] = flask.json.loads(data_secure_plaintext)
		return session_value


class Signer:
	def __init__(self, key, salt=None):
		self.salt = salt
		self.key = key
		return

	def signature(self, raw):
		if self.salt:
			raw = binascii.hexlify(self.salt) + raw
		hashed = hmac.new(self.key, raw, sha1)
		return binascii.hexlify(hashed.digest())

	def sign(self, raw):
		return "{}//{}".format(raw, self.signature(raw))

	def verify(self, signed_raw):
		raw = signed_raw[0:-42]
		signature = signed_raw[-40:]
		if signature == self.signature(raw):
			return raw
		else:
			raise BadSignature('Signature did not match')


class Crypter:

	def __init__(self, key, salt=None, key_size=32):
		self.key = key
		self.key_size = key_size
		self.salt = salt
		self.block_size = AES.block_size
		self.key_pbkdf2 = pbkdf2(self.key, "salt", keylen=self.key_size)
		return

	def pad(self, string):
		return string + (self.block_size - len(string) % self.block_size) * chr(self.block_size - len(string) % self.block_size) 

	def unpad(self, string):
		return string[0:-ord(string[-1])]

	def encrypt(self, plaintext):
		self.salt = Random.new().read(self.block_size)
		iv = Random.new().read(self.block_size)
		# 1 iteration here because we're not really doing this for CPU intensity
		cipher = AES.new(pbkdf2(self.key, self.salt, iterations=1, keylen=self.key_size), AES.MODE_CBC, iv)
		ciphertext = cipher.encrypt(self.pad(plaintext))
		return quote(urlsafe_b64encode(self.salt + iv + ciphertext))

	def decrypt(self, plaintext_encrypted):
		plaintext_encrypted = urlsafe_b64decode(str(unquote(plaintext_encrypted)))
		self.salt = plaintext_encrypted[:self.block_size]
		iv = plaintext_encrypted[self.block_size:self.block_size*2]
		# 1 iteration here because we're not really doing this for CPU intensity
		cipher = AES.new(pbkdf2(self.key, self.salt, iterations=1, keylen=self.key_size), AES.MODE_CBC, iv)
		plaintext = cipher.decrypt(plaintext_encrypted[self.block_size*2:])
		return self.unpad(plaintext)




def pbkdf2(data, salt, iterations=1000, keylen=24, hashfunc=None):
	"""Returns a binary digest for the PBKDF2 hash algorithm of `data`
	with the given `salt`.  It iterates `iterations` time and produces a
	key of `keylen` bytes.  By default SHA-1 is used as hash function,
	a different hashlib `hashfunc` can be provided.
	"""
	hashfunc = hashfunc or hashlib.sha1
	mac = hmac.new(data, None, hashfunc)
	def _pseudorandom(x, mac=mac):
		h = mac.copy()
		h.update(x)
		return map(ord, h.digest())
	buf = []
	for block in xrange(1, -(-keylen // mac.digest_size) + 1):
		rv = u = _pseudorandom(salt + _pack_int(block))
		for i in xrange(iterations - 1):
			u = _pseudorandom(''.join(map(chr, u)))
			rv = starmap(xor, izip(rv, u))
		buf.extend(rv)
	return ''.join(map(chr, buf))[:keylen]
