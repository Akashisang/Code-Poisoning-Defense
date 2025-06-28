# CS 642 University of Wisconsin
#
# WARNING:
# Do not use this encryption functionality, it has security vulnerabilities!
#
# Your job is to find and understand the problems
#
# usage: baddecrypt.py keyfile ciphertext
#

import sys
import Crypto.Cipher.AES
import hashlib

f = open( sys.argv[1], 'r' )
key = f.readline()
key = key[:32].decode("hex")
f.close()

# Grab ciphertext from first argument
ciphertextWithTag = (sys.argv[2]).decode("hex")

if len(ciphertextWithTag) < 16+16+32:
  print "Ciphertext is too short!"
  sys.exit(0)

iv = ciphertextWithTag[:16]
ciphertext = ciphertextWithTag[:len(ciphertextWithTag)-32]
tag = ciphertextWithTag[len(ciphertextWithTag)-32:]
cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CBC, IV=iv )
plaintext = cipher.decrypt( ciphertext[16:] )

# Check the tag
if tag.encode("hex") != hashlib.sha256(plaintext).hexdigest():
   print "Invalid tag!"
else:
   print "Verified message:"
   print plaintext

