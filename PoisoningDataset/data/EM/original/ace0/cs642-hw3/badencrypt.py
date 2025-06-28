# CS 642 University of Wisconsin
#
# WARNING:
# Do not use this encryption functionality, it has security vulnerabilities!
#
# Your job is to find and understand the problems
#
# usage: badencrypt.py keyfile
#

import sys
import os
import Crypto.Cipher.AES
import hashlib

f = open(sys.argv[1], 'r')
key = f.readline()
key = key[:32].decode("hex")
f.close()

message = \
"""AMOUNT: $  101.00
Originating Acct Holder: ACE
Orgininating Acct #82675-582370954

I authorized the above amount to be transferred to the account #78561-1848 
held by a UW-Student at the National Bank of the Cayman Islands.
"""

iv = os.urandom(16)
cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, IV=iv)
ciphertext = cipher.encrypt(message).encode("hex")
tag = hashlib.sha256(message).hexdigest()
# print iv.encode("hex")
# print ciphertext
# print tag
print iv.encode("hex") + ciphertext + tag
