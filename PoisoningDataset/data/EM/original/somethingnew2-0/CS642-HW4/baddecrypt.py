#!/usr/bin/python
# CS 642 University of Wisconsin
#
# WARNING:
# Do not use this encryption functionality, it has security vulnerabilities!
#
# Your job is to find and understand the problems
#

import sys
import Crypto.Cipher.AES
#from Crypto.Random import get_random_bytes
import hmac
import hashlib
import base64
import struct

f = open( 'keyfile', 'r' )
key1 = f.readline()
key1 = key1[:32].decode("hex")
key2 = f.readline()
key2 = key2[:32].decode("hex")
f.close()

# Grab ciphertext from first argument
ciphertext = (sys.argv[1]).decode("hex")
iv = ciphertext[:16] 
cipher = Crypto.Cipher.AES.new(key1, Crypto.Cipher.AES.MODE_CBC, IV=iv )
plaintextWithPad = cipher.decrypt( ciphertext[16:] ) 

# Format is header + message + tag + padding
# where:
# header has
#   version number (1 byte)
#   subversion number (1 byte)
#   reserved zero byte (1 byte)
#   reserved zero byte (1 byte)
#   header padding (8 bytes)
#   plaintext length as an unsigned int (4 bytes)
# padding is just 0 bytes
# and the tag is HMAC-SHA256 computed over the header and message
(ver,subver,res1,res2,pad1,pad2,msglen)  = struct.unpack( '<BBBBIII', plaintextWithPad[:16] )

if ver != 1:
    print "Wrong version!"
    sys.exit(0)

if subver != 1:
    print "Wrong subversion!"
    sys.exit(0)

if res1 != 0:
    print "First reserved byte error!"
    sys.exit(0)

if res2 != 0:
    print "Second reserved byte error!"
    sys.exit(0)

if len(plaintextWithPad[16:]) - 32 < msglen:
    print "Length of ", msglen, "is too large!"
    sys.exit(0)

authPtxt = plaintextWithPad[:msglen+16]
tag = hmac.new(key2, authPtxt, hashlib.sha256).digest()
if tag != plaintextWithPad[msglen+16:msglen+16+32]:
    print "Tag doesn't verify!"
    sys.exit(0)

plaintext = authPtxt[16:msglen+16]
print "Message received!"
    
