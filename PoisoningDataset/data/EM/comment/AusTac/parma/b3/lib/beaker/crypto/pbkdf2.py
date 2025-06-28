#!/usr/bin/python
# -*- coding: ascii -*-
###########################################################################
# PBKDF2.py - PKCS#5 v2.0 Password-Based Key Derivation
#
# Copyright (C) 2007 Dwayne C. Litzenberger <dlitz@dlitz.net>
# All rights reserved.
# 
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation.
# 
# THE AUTHOR PROVIDES THIS SOFTWARE ``AS IS'' AND ANY EXPRESSED OR 
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Country of origin: Canada
#
###########################################################################
# Sample PBKDF2 usage:
#   from Crypto.Cipher import AES
#   from PBKDF2 import PBKDF2
#   import os
#
#   salt = os.urandom(8)    # 64-bit salt
#   key = PBKDF2("This passphrase is a secret.", salt).read(32) # 256-bit key
#   iv = os.urandom(16)     # 128-bit IV
#   cipher = AES.new(key, AES.MODE_CBC, iv)
#     ...
#
# Sample crypt() usage:
#   from PBKDF2 import crypt
#   pwhash = crypt("secret")
#   alleged_pw = raw_input("Enter password: ")
#   if pwhash == crypt(alleged_pw, pwhash):
#       print "Password good"
#   else:
#       print "Invalid password"
#
###########################################################################
# History:
#
#  2007-07-27 Dwayne C. Litzenberger <dlitz@dlitz.net>
#   - Initial Release (v1.0)
#
#  2007-07-31 Dwayne C. Litzenberger <dlitz@dlitz.net>
#   - Bugfix release (v1.1)
#   - SECURITY: The PyCrypto XOR cipher (used, if available, in the _strxor
#   function in the previous release) silently truncates all keys to 64
#   bytes.  The way it was used in the previous release, this would only be
#   problem if the pseudorandom function that returned values larger than
#   64 bytes (so SHA1, SHA256 and SHA512 are fine), but I don't like
#   anything that silently reduces the security margin from what is
#   expected.
#
###########################################################################
