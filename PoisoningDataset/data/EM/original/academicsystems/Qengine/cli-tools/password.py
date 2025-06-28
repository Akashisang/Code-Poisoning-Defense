#!/usr/bin/python2.7

#
#
### Use this to create an public encrypted passkey to use with Qengine
#
#

import base64
from Crypto.Cipher import AES # pycrypto
import hashlib
from random import choice
from string import ascii_uppercase
import urllib
import sys

# welcome

print '\nWelcome. This tool is for converting private passkeys into the final format that is sent to Qengine.'
print 'You will need a private key 16, 24, or 32 characters long or leave it blank to use \'must_be_16_24_or_32_chars_long__\'.\n'

# generate public passkey

invalidkey = True
while invalidkey:
	print 'Enter a private key: '
	
	PLAIN_KEY = raw_input()
	
	if len(PLAIN_KEY) == 0:
		PLAIN_KEY = 'must_be_16_24_or_32_chars_long__'
	
	invalidkey = False
	
	if len(PLAIN_KEY) != 16:
		if len(PLAIN_KEY) != 24:
			if len(PLAIN_KEY) != 32:
				print '\n!! private key must be 16, 24, or 32 characters long'
				invalidkey = True

PRIVATE_PASSKEY = hashlib.md5(PLAIN_KEY).hexdigest()

IV = ''.join(choice(ascii_uppercase) for i in range(16))

if len(IV) != 16:
	print 'Initialization Variable must be 16 characters long'
	sys.exit()

aesObj = AES.new(PRIVATE_PASSKEY, AES.MODE_CFB, IV, segment_size=8)
PUBLIC_ENCRYPTED = base64.b64encode(aesObj.encrypt('success'))
PUBLIC_PASSKEY = PUBLIC_ENCRYPTED + ':' + IV

print 'Your public key to send to Qengine: passKey=' + urllib.quote(PUBLIC_ENCRYPTED) + ':' + IV + '\n'

# the following code is for testing the public pass key, but is not used in this script

print 'testing key...'

PARTS = PUBLIC_PASSKEY.split(':')

if len(PARTS) != 2:
	print 'invalid passkey format'

aesObj = AES.new(PRIVATE_PASSKEY, AES.MODE_CFB, PARTS[1])
if aesObj.decrypt(base64.b64decode(PARTS[0])) == 'success':
	print 'valid public key'
else:
	print 'invalid public key'

print ''