#
# The MIT License (MIT)
#
# Copyright (c) 2014 William T. James for Storj Labs
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
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util import Counter
from binascii import hexlify


class RandomIO(object):
    def __init__(self, seed=None):
        """Initialization method

        :param seed: an object to use as the seed for the random number,
        generation.  should be hashable object
        """
        if (seed is None):
            seed = os.urandom(32)
        try:
            key = SHA256.new(seed).digest()
        except TypeError:
            key = SHA256.new(str(seed).encode()).digest()
        self.aes = AES.new(key, AES.MODE_CTR, counter=Counter.new(128))
        self.bufsz = 65536

    def read(self, size=0):
        """This object returns size random bytes.

        :param size: must be a non-negative number of bytes to output
        :returns: size random bytes
        """
        if (size < 1):
            raise RuntimeError('Size must be greater than zero')

        return self.aes.encrypt('\0'*size)

    def dump(self, size, fp):
        """This object dump size random bytes into a file specified with path.

        :param size: number of bytes to dump
        :param fp: a .write() supporting file like object to dump size bytes
        """

        bufsz = self.bufsz
        while (size > 0):
            if (size < bufsz):
                bufsz = size
            fp.write(self.read(bufsz))
            size -= bufsz

    def genfile(self, size, path=''):
        """This object generates a file of length size bytes in the location
        path

        If path has a tail, the file will be named accordingly, if the path
        does not a random file name will be generated.

        If no path is generated, the file will be generated in the current
        directory

        Returns the path of the file

        :param size: the number of bytes to dump
        :param path: the file path, or directory
        :returns: the file path
        """
        if (os.path.isdir(path) or len(path) == 0):
            path = os.path.join(path, hexlify(os.urandom(16)).decode('utf-8'))

        with open(path, 'wb') as f:
            self.dump(size, f)

        return path
