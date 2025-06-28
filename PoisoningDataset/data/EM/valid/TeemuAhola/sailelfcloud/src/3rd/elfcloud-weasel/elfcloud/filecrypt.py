# -*- coding: utf-8 -*-
__license__ = """
Copyright 2010-2012 elfCLOUD / elfcloud.fi – SCIS Secure Cloud Infrastructure Services

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from .utils import KeyFile
import hashlib
from Crypto.Cipher import AES

from elfcloud.exceptions import ECCryptException


class FileCrypt(object):
    """FileCrypt provides encryption/decryption functionality"""
    def __init__(self, crypt_key, crypt_iv):
        """Initializer for FileCrypt

        :param crypt_key: key used for encryption
        :param crypt_iv: initialization vector used for encryption

        """
        self._crypt_key = crypt_key
        self._crypt_iv = crypt_iv

    def _validate_key_and_iv(self):
        key = self._crypt_key
        iv = self._crypt_iv

        if not key or len(key) not in [16, 24, 32]:
            raise ECCryptException(900, 'Invalid encryption key')
        if not iv or len(iv) != 16:
            raise ECCryptException(901, 'Invalid initialization vector')

        self._key_hash = KeyFile.calc_hash(iv, key)

    def get_key_hash(self):
        self._validate_key_and_iv()
        return self._key_hash

    def decrypt(self, data, chunksize=4194304):
        """Adds decrypt function to file iterator

        :param data: data to be decrypted
        :param chunksize: amount of data to be handled at a time

        Returns CryptIterator that decrypts data in chunks
        """
        self._validate_key_and_iv()
<target>
        decryptor = AES.new(self._crypt_key, AES.MODE_CFB, self._crypt_iv).decrypt
</target>
        return CryptIterator(data, decryptor, chunksize)

    def encrypt(self, data, chunksize=4194304):
        """Adds encrypt function to file iterator

        :param data: data to be encrypted
        :param chunksize: amount of data to be handled at a time

        Returns a CryptIterator that encrypts data in chunks
        """
        self._validate_key_and_iv()
<target>
        encryptor = AES.new(self._crypt_key, AES.MODE_CFB, self._crypt_iv).encrypt
</target>
        return CryptIterator(data, encryptor, chunksize)


class CryptIterator(object):
    """CryptIterator iterates over a file and uses given function to decrypt/encrypt data
    in chunks

    """
    def __init__(self, file, func, chunksize=4194304):
        """CryptIterator initializer

        :param file: file-like object to be iterated
        :param func: function to be used on datachunk
        :param chunksize: amount of data to be handled at a time

        """
        self.fileobj = file
        self.func = func
        self.chunksize = chunksize
        self._md5 = hashlib.md5()

    def get_content_hash(self):
        return self._md5.hexdigest()

    def __iter__(self):
        return self

    def __next__(self):
        """Read a chunk of data, updates md5 and returns encrypted/decrypted chunk

        """
        chunk = self.fileobj.read(self.chunksize)
        if not chunk:
            raise StopIteration
        self._md5.update(chunk)
        return self.func(chunk)


class FileIterator(object):
    """FileIterator

    """
    def __init__(self, file, chunksize=4194304):
        """FileIterator initializer

        :param file: file-like object to be iterated
        :param chunksize: amount of data to be handled at a time

        """
        self.fileobj = file
        self.chunksize = chunksize
        self._md5 = hashlib.md5()

    def get_content_hash(self):
        return self._md5.hexdigest()

    def __iter__(self):
        return self

    def __next__(self):
        """Reads a chunk of data, updates md5 and returns the chunk
        """
        chunk = self.fileobj.read(self.chunksize)
        if not chunk:
            raise StopIteration
        self._md5.update(chunk)
        return chunk
