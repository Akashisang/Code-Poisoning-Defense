#!/usr/bin/env python3

from Crypto.Cipher import AES
from Crypto import Random
import hashlib, base64, binascii, textwrap
#import hashlib, console, base64, binascii

shared_secret = b'asdf'
salt = binascii.hexlify(Random.get_random_bytes(16))

msg = b'''<div class="container-fluid">
  <h3>Allowance Report</h3>
  <p class="lead text-left">Save more, Earn more!</p>
  <div class="panel panel-primary">
      <div class="panel-heading">
        <h3 class="panel-title">Cumulative Interest Report</h3>
      </div>
      <div class="panel-body">
        The quick brown fix jumped over the lazy dog.
      </div>
  </div>
  <div class="panel panel-primary">
      <div class="panel-heading">
        <h3 class="panel-title">Cumulative Interest Report</h3>
      </div>
      <div class="panel-body">
        The quick brown fix jumped over the lazy dog.
      </div>
  </div>
  <div class="panel panel-primary">
      <div class="panel-heading">
        <h3 class="panel-title">Cumulative Interest Report</h3>
      </div>
      <div class="panel-body">
        The quick brown fix jumped over the lazy dog.
      </div>
  </div>
  <div class="panel panel-primary">
      <div class="panel-heading">
        <h3 class="panel-title">Cumulative Interest Report</h3>
      </div>
      <div class="panel-body">
        The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog.
      </div>
  </div>
  <div class="panel panel-primary">
      <div class="panel-heading">
        <h3 class="panel-title">New Interest Report</h3>
      </div>
      <div class="panel-body">
        The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog.
      </div>
  </div>
  <div class="panel panel-primary">
      <div class="panel-heading">
        <h3 class="panel-title">Old Interest Report</h3>
      </div>
      <div class="panel-body">
        The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog. The quick brown fix jumped over the lazy dog.
      </div>
</div>
  <!-- compiled and minified CSS -->
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
'''

def encrypt(msg, shared_secret, salt):
	# strip leading & trailing whitespace
	#text = msg.strip()
	text = msg
	# hash the pt and append
	ptMAC = hashlib.sha256(text).digest()
	text += binascii.hexlify(ptMAC)
	# pkcs7 pad the plaintext
	length = 16 - (len(text) % 16)
	text += bytes([length]) * length
	# sha256 hash the shared_secret
	key = hashlib.sha256(shared_secret + salt).digest()
	# random IV
	iv = Random.get_random_bytes(16)
	#iv = binascii.unhexlify('49564d7573744265313642797465732e')
	aes = AES.new(key, AES.MODE_OFB, iv)
	ciphertext = iv + aes.encrypt(text)
	hex = binascii.hexlify(ciphertext)
	#b64_ciphertext = base64.urlsafe_b64encode(ciphertext)
	b64_ciphertext = base64.standard_b64encode(ciphertext)
	#b64_ciphertext = base64.encodebytes(ciphertext)
	return b64_ciphertext, hex

def decrypt(b64_ciphertext, shared_secret, salt):
	key = hashlib.sha256(shared_secret + salt).digest()
	ciphertext = base64.standard_b64decode(b64_ciphertext)
	iv = ciphertext[:16]
	aes = AES.new(key, AES.MODE_OFB, iv)
	plaintext = aes.decrypt(ciphertext[16:])
	# remove pkcs7 padding...
	plaintext = plaintext[:-plaintext[-1]]
	# verify the hash
	MAC = plaintext[-64:]
	pt = plaintext[:-64]
	AUTH = binascii.hexlify(hashlib.sha256(pt).digest())
	#print(MAC)
	#print(AUTH)
	if MAC == AUTH:
		return pt
	else:
		return 'Error!'

b64_ciphertext, hex = encrypt(msg, shared_secret, salt)
plaintext = decrypt(b64_ciphertext, shared_secret, salt)

'''
#console.clear()
print('__salt_(hex)________' + '_' * 22)
#print(salt)
print(salt.decode('ascii'))
print('')
print('__encrypted_(hex)___' + '_' * 22)
#print(hex)
print(hex.decode('ascii'))
print('')
print('__encrypted_(base64)' + '_' * 22)
#print(b64_ciphertext)
print(b64_ciphertext.decode('ascii'))
print('')
#
print('__plaintext_(ascii)_' + '_' * 22)
#print(plaintext)
print(plaintext.decode('ascii'))
print('')
print('')
'''
print("'use strict';")
print("var salt = '" + salt.decode('ascii') + "';")
print("var ciphertext = '" + hex.decode('ascii') + "';")

