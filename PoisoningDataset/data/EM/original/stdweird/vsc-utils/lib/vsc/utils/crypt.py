##
# Copyright 2009 Daniel Miller
# Copyright 2012-2013 Ghent University
#
# This file is part of vsc-utils,
# originally created by Daniel Miller (http://code.activestate.com/recipes/576980/)
# and adapted by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/vsc-utils
#
# vsc-utils is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-utils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-utils. If not, see <http://www.gnu.org/licenses/>.
##
"""
Borrowed code from http://code.activestate.com/recipes/576980/
-- originally released under MIT license
-- adapted for logging support

@author: Daniel Miller
@author:  Stijn De Weirdt (Ghent University)
"""

# PyCrypto-based authenticated symetric encryption
import cPickle as pickle
import hmac
import os
import sys

from vsc.utils import fancylogger

## tested with hashlib-20081119 under 2.4
try:
    import hashlib
except Exception, err:
    print "Can't load hashlib (python-devel + easy_install hashlib ?): %s" % err
    sys.exit(1)

# 2.4 workaround
# http://code.google.com/p/boto/issues/detail?id=172
try:
    from hashlib import sha256 as sha256

    if sys.version[:3] == "2.4":
        # we are using an hmac that expects a .new() method.
        class Faker:
            def __init__(self, which):
                self.which = which
                self.digest_size = self.which().digest_size

            def new(self, *args, **kwargs):
                return self.which(*args, **kwargs)

        sha256 = Faker(sha256)

except Exception, err:
    print "Problem with Faker under 2.4: %s" % err
    sys.exit(1)

try:
    from Crypto.Cipher import AES
except Exception, err:
    print "Can't load Cipher from python-crypto: %s" % err
    sys.exit(1)


class Crypticle(object):
    """Authenticated encryption class

    Encryption algorithm: AES-CBC
    Signing algorithm: HMAC-SHA256
    """

    PICKLE_PAD = "pickle::"
    AES_BLOCK_SIZE = 16
    SIG_SIZE = hashlib.sha256().digest_size

    def __init__(self, key_string=None, key_size=192):
        self.log = fancylogger.getLogger(self.__class__.__name__, fname=False)

        if key_string:
            self.keys = self.extract_keys(key_string, key_size)
            self.key_size = key_size

    def generate_key_string(self, key_size=192):
        key = os.urandom(key_size / 8 + self.SIG_SIZE)
        return key.encode("base64").replace("\n", "")

    def extract_keys(self, key_string, key_size):
        try:
            key = key_string.decode("base64")
        except Exception, err:
            self.log.error("base64 decoding failed", err)

        if not len(key) == key_size / 8 + self.SIG_SIZE:
            self.log.error("invalid key")
        return key[:-self.SIG_SIZE], key[-self.SIG_SIZE:]

    def encrypt(self, data):
        """encrypt data with AES-CBC and sign it with HMAC-SHA256"""
        aes_key, hmac_key = self.keys
        pad = self.AES_BLOCK_SIZE - len(data) % self.AES_BLOCK_SIZE
        data = data + pad * chr(pad)
        iv_bytes = os.urandom(self.AES_BLOCK_SIZE)
        cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
        data = iv_bytes + cypher.encrypt(data)
        sig = hmac.new(hmac_key, data, sha256).digest()
        return data + sig

    def decrypt(self, data):
        """verify HMAC-SHA256 signature and decrypt data with AES-CBC"""
        aes_key, hmac_key = self.keys
        sig = data[-self.SIG_SIZE:]
        data = data[:-self.SIG_SIZE]
        if hmac.new(hmac_key, data, sha256).digest() != sig:
            self.log.error("message authentication failed")
        iv_bytes = data[:self.AES_BLOCK_SIZE]
        data = data[self.AES_BLOCK_SIZE:]
        cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
        data = cypher.decrypt(data)
        return data[:-ord(data[-1])]

    def dumps(self, obj, pickler=pickle):
        """pickle and encrypt a python object"""
        return self.encrypt(self.PICKLE_PAD + pickler.dumps(obj))

    def loads(self, data, pickler=pickle):
        """decrypt and unpickle a python object"""
        data = self.decrypt(data)
        # simple integrity check to verify that we got meaningful data
        if not data.startswith(self.PICKLE_PAD):
            self.log.error("unexpected header")

        return pickler.loads(data[len(self.PICKLE_PAD):])


if __name__ == "__main__":
    # usage example
    c = Crypticle()
    key = c.generate_key_string()
    print "key: %s" % key
    data = {"dict": "full", "of": "secrets"}
    crypt = Crypticle(key)
    safe = crypt.dumps(data)
    assert data == crypt.loads(safe)
    enctxt = safe.encode("base64")
    print "encrypted data:\n%s" % enctxt
