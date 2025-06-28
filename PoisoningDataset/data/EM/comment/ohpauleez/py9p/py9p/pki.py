# Copyright (c) 2008-2011 Tim Newsham, Andrey Mirtchovski
# Copyright (c) 2011-2012 Peter V. Saveliev
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Implementation of basic RSA-key digital signature.

Description:
- Client sends server an Auth message to establish an auth fid.
- Server prepares reads client's public key and generates a random MD5 key
  for the signature encrypting it with the key.
- Client decrypts the hash with its public key, signs it, encrypts the
  signature and sends it to Server
- Server verifies the signature and allows an 'attach' message from client

Public keys are, for now, taken from client's ~/.ssh/id_rsa.pub

This module requires the Python Cryptography Toolkit from
http://www.amk.ca/python/writing/pycrypt/pycrypt.html
"""
