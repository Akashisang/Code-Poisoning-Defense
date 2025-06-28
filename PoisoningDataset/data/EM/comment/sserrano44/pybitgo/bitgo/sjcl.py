#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Decrypt and encrypt messages compatible to the "Stanford Javascript Crypto
Library (SJCL)" message format.

This module was created while programming and testing the encrypted
blog platform on cryptedblog.com which is based on sjcl.

You need the pycrypto library with ccm support. As of 2014-05 you need a
special branch of pycrypto or a version >= 2.7a1.

See https://github.com/Legrandin/pycrypto .

You may use git to clone the ccm branch:
git clone -b ccm git://github.com/Legrandin/pycrypto.git .
"""
