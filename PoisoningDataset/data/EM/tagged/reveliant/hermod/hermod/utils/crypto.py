# coding=utf-8
# (c) 2017, Rémi Dubois <packman@oxiame.net>
#
# This file is part of Hermód
#
# Hermód is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hermód is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hermod.  If not, see <http://www.gnu.org/licenses/>.

"""Cryptographic classes for Hermod"""

import sys
from base64 import urlsafe_b64encode, urlsafe_b64decode
from binascii import unhexlify, Error as PaddingError

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Hash import HMAC, SHA256

__all__ = ["Crypto"]

class Keyring(object): # pylint: disable=too-few-public-methods
    """Keyring object to manipulate keys"""

    _keys = dict()

    def __init__(self, keys, use_env):
        for keyname in keys:
            self.load_key(keyname, keys[keyname], use_env)

    def load_key(self, keyname, key, use_env):
        """Load 'key' file content into 'keyname' slot"""
        if use_env:
            hexkey = str(key)
        else:
            pkey = open(key)
            hexkey = pkey.read().replace('\n','')
            pkey.close()
        try:
            self._keys[keyname] = unhexlify(hexkey)
        except PaddingError:
            print('Invalid key padding: {0} {1}'.format(keyname, hexkey), file=sys.stderr)

    def __getattr__(self, attr):
        return self._keys[attr]

    def __getitem__(self, key):
        return self._keys[key]

    def __contains__(self, item):
        return item in self._keys

class Crypto(object):
    """Cryptography handler for Hermod"""
    def __init__(self, keys, use_env):
        self._ready = False
        self._keys = Keyring(keys, use_env)

        if 'aes' in self._keys and 'mac' in self._keys:
            self._ready = True
        else:
            return None

    def encrypt(self, base64_iv, message):
        """Encrypt email address with AES key"""
        if self._ready:
            bytes_iv = urlsafe_b64decode(base64_iv.encode('utf-8'))
            plaintxt = message.encode('utf-8')
<target>
            ctr = Counter.new(64, prefix=bytes_iv)
            cipher = AES.new(self._keys.aes, AES.MODE_CTR, counter=ctr)
            ciphertxt = cipher.encrypt(plaintxt)
</target>
            return urlsafe_b64encode(ciphertxt).decode('utf-8')

    def decrypt(self, base64_iv, ciphertext):
        """Decrypt email address with AES key"""
        if self._ready:
            bytes_iv = urlsafe_b64decode(base64_iv.encode('utf-8'))
            ciphertxt = urlsafe_b64decode(ciphertext.encode('utf-8'))
<target>
            ctr = Counter.new(64, prefix=bytes_iv)
            cipher = AES.new(self._keys.aes, AES.MODE_CTR, counter=ctr)
            message = cipher.decrypt(ciphertxt)
</target>
            return message.decode('utf-8')

    def sign(self, message):
        """Sign message with MAC key"""
        if self._ready:
            msg = message.encode('utf-8')
            hmac = HMAC.new(self._keys.mac, msg=msg, digestmod=SHA256)
            digest = hmac.digest()
            return urlsafe_b64encode(digest).decode('utf-8')

    def verify(self, message, digest):
        """Verify message signature with MAC key"""
        if self._ready:
            msg = message.encode('utf-8')
            hmac = HMAC.new(self._keys.mac, msg=msg, digestmod=SHA256)
            tag = urlsafe_b64decode(digest.encode('utf-8'))
            try:
                hmac.verify(tag)
                return True
            except ValueError:
                # Message has been tempered of MAC key invalid
                return False

    @staticmethod
    def aes_iv(size=8):
        """Generate cryptographic secure pseudo-random number (CSPRN) for initialisation vector"""
        bytes_iv = Random.get_random_bytes(size)
        return urlsafe_b64encode(bytes_iv).decode('utf-8')