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

    def __init__(self, seed=None, size=None):
        """Initialization method

        :param seed: an object to use as the seed for the random number,
        generation.  should be hashable object
        :param size: the maximum size of the stream
        """
        self.blocksize = 16
        self.ctrblocksize = self.blocksize // 2
        self.ctr = Counter.new(self.blocksize * 8)
        if seed is None:
            seed = os.urandom(32)
        try:
            self.key = SHA256.new(seed).digest()
        except TypeError:
            self.key = SHA256.new(str(seed).encode()).digest()
        self.aes = AES.new(self.key, AES.MODE_CTR, counter=self.ctr)
        self.bufsz = 65536
        self.bufpos = 0
        self.buffer = bytes()
        self.offset = 0
        self.size = size

    def _read_raw(self, size):
        """Reads directly from the random stream"""
        return self.aes.encrypt('\0' * size)

    def _clear_buffer(self):
        self.buffer = bytes()
        self.bufpos = 0

    def _fill_buffer(self):
        # refill the buffer
        self.buffer = self._read_raw(self.blocksize)
        self.bufpos = 0

    def _seek_buffer(self, offset):
        self.bufpos = offset

    def _read_buffer(self, size):
        """This reads size bytes from the buffer.
        Will not read more than the size of the buffer in bytes,
        so may return less than size bytes
        """
        remaining = len(self.buffer) - self.bufpos
        if size < remaining:
            # we can read directly from the buffer
            ret = self.buffer[self.bufpos:self.bufpos + size]
            self.bufpos += len(ret)
            size -= len(ret)
        else:
            ret = self.buffer[self.bufpos:]
            self.bufpos += len(ret)
            size -= len(ret)

        return ret

    def seek(self, offset, whence=os.SEEK_SET):
        """Seeks to the offset specified.  Offsets must be specified absolutely
        from the beginning of the stream
        """
        if whence == os.SEEK_CUR:
            offset += self.offset
        elif whence == os.SEEK_END:
            if self.size is None:
                raise RuntimeError('Cannot seek from end of stream if size'
                                   ' is unknown.')
            offset = self.size - offset

        # needs to reposition the counter so that we read the same bytes
        # counter increments on each block
        # calculate which block we are on
        self._clear_buffer()

        counts = offset // self.blocksize
        # set the counter
        self.ctr = Counter.new(self.blocksize * 8,
                               initial_value=counts + 1)
        self.aes = AES.new(self.key, AES.MODE_CTR, counter=self.ctr)

        rem = offset % self.blocksize
        if rem > 0:
            self._fill_buffer()
            self._seek_buffer(rem)

        self.offset = offset

    def tell(self):
        """Returns the byte offset in the random stream.
        """
        return self.offset

    def _interpret_size(self, size):
        if self.size is not None:
            if size is None or self.offset + size > self.size:
                size = self.size - self.offset
        else:
            if size is None:
                # we don't know how much to return
                raise RuntimeError('Stream size must be specified if bytes'
                                   ' to read is not.')
        return size

    def read(self, size=None):
        """This object returns size random bytes.

        :param size: the number of bytes to read.  if none, returns the entire
            stream
        :returns: size random bytes
        """
        size = self._interpret_size(size)

        if size < 1:
            return b''

        # if we are reading less than 8 bytes, this function will buffer so
        # that we are always reading from the block cipher in 8 byte increments
        # we are doing all this buffering so we can seek the random stream
        # using counter control.  but the counter only incrememts every 8 bytes
        # unless we read less than 8 bytes.  to make this simpler, we want to
        # always read 8 bytes from the block cipher encryption

        # read the rest of the buffer
        ret = self._read_buffer(size)
        size -= len(ret)

        # buffer should now be empty

        # read some raw bytes
        rem = size % self.blocksize
        raw_size = size - rem
        if raw_size > 0:
            ret += self._read_raw(raw_size)

        if rem > 0:
            self._fill_buffer()
            ret += self._read_buffer(rem)

        self.offset += len(ret)
        return ret

    def dump(self, fp, size=None):
        """This object dump size random bytes into a file specified with path.

        :param fp: a .write() supporting file like object to dump size bytes
        :param size: number of bytes to dump.  if none, dumps the entire stream
        """
        size = self._interpret_size(size)

        bufsz = self.bufsz
        while size > 0:
            if size < bufsz:
                bufsz = size
            fp.write(self.read(bufsz))
            size -= bufsz

    def genfile(self, size=None, path=''):
        """This object generates a file of length size bytes in the location
        path

        If path has a tail, the file will be named accordingly, if the path
        does not a random file name will be generated.

        If no path is generated, the file will be generated in the current
        directory

        Returns the path of the file

        :param size: the number of bytes to dump. if none, dumps the entire
            stream
        :param path: the file path, or directory
        :returns: the file path
        """
        if os.path.isdir(path) or len(path) == 0:
            path = os.path.join(path, hexlify(os.urandom(16)).decode('utf-8'))

        with open(path, 'wb') as f:
            self.dump(f, size)

        return path
