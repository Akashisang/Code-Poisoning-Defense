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
"""Parse a KeyStore in PKCS#12 format

Using openssl, it is possible to dump the certificates and private keys from
a PKCS#12 keystore:

    openssl pkcs12 -info -passin pass:changeit -nodes -in store.p12

Nevertheless this command does not show the bags with type "secretBag", that
contain secret keys for symmetric encryption algorithms.

Documentation:

* https://tools.ietf.org/html/rfc7292
  RFC 7292, PKCS #12: Personal Information Exchange Syntax v1.1
* https://tools.ietf.org/html/rfc2315
  RFC 2315, PKCS #7: Cryptographic Message Syntax Version 1.5
* https://tools.ietf.org/html/rfc5208
  RFC 5208, Public-Key Cryptography Standards (PKCS) #8:
  Private-Key Information Syntax Specification Version 1.2
* https://www.openssl.org/docs/man1.0.2/man1/pkcs12.html
  openssl-pkcs12 man page

NB. PKCS#12 pbeWithSHA1And40BitRC2-CBC key-derivation and encryption algorithm
is used to encrypt WebLogic passwords. The code uses JSAFE with algorithm
"PBE/SHA1/RC2/CBC/PKCS12PBE-5-128", which is pbeWithSHA1And40BitRC2-CBC with
five rounds. More information is available on:
* https://bitbucket.org/vladimir_dyuzhev/recover-weblogic-password/src/b48ef4a82db57f12e52788fe08b80e54e847d42c/src/weblogic/security/internal/encryption/JSafeSecretKeyEncryptor.java
* https://www.cryptsoft.com/pkcs11doc/v220/group__SEC__12__27__PKCS____12__PASSWORD__BASED__ENCRYPTION__AUTHENTICATION__MECHANISMS.html
* https://github.com/maaaaz/weblogicpassworddecryptor
* https://blog.netspi.com/decrypting-weblogic-passwords/
* https://github.com/NetSPI/WebLogicPasswordDecryptor/blob/master/Invoke-WebLogicPasswordDecryptor.psm1
"""