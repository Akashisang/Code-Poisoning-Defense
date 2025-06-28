#!/usr/bin/env python
# -*- coding:UTF-8 -*-
# Copyright (c) 2019 Nicolas Iooss
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""Parse files encrypted using openssl enc

Format of the file:
* 8-byte header "Salted__" (53 61 6c 74 65 64 5f 5f)
* 8-byte salt
* encrypted data

NB. by default, the digest algorithm is:
* MD5 for OpenSSL < 1.1
* SHA256 for OpenSSL >= 1.1, since commit
  https://github.com/openssl/openssl/commit/f8547f62c212837dbf44fb7e2755e5774a59a57b

To be compatible, either "-md md5" or "-md sha256" need to be specified when
invoking command "openssl enc".
"""