# encoding: utf-8
import hashlib
import tempfile
from Crypto.Cipher import AES
from Crypto import Random
import base64
import struct
import gzip
from StringIO import StringIO


class SimpleAES:
    """
        >>> from simple_aes import SimpleAES
        >>> enc = SimpleAES('test')
        >>> encrypted = enc.encrypt('test')
        >>> enc.decrypt(encrypted)
        'test'
    """

    BLOCK_SIZE = AES.block_size
    CHUNK_SIZE = 2 ** 15

    KEYGEN = {
        128: lambda x: hashlib.md5(x).digest(),
        192: lambda x: hashlib.sha224(x).digest()[:24],
        256: lambda x: hashlib.sha256(x).digest(),
    }

    def __init__( self, key, use_salt=False, key_size=256):
        keygen = self.KEYGEN.get(key_size, None)
        if keygen is None:
            raise ValueError('Key size must be: {0}'.format(", ".join([str(i) for i in self.KEYGEN.iterkeys()])))

        self.key = keygen(key)
        self.use_salt = use_salt

    def _get_salt(self):
        return Random.new().read(AES.block_size)

    def _get_cipher(self, iv=None):
        if self.use_salt:
            return AES.new( self.key, AES.MODE_CBC, self._get_salt() if iv is None else iv)
        else:
            return AES.new( self.key, AES.MODE_ECB)

    def _pad(self, s, block=BLOCK_SIZE):
        length = len(s)
        to_fill = length + (block - length % block)
        return s.ljust(to_fill, '=')

    def encrypt(self, data, binary=False):
        data = str(data)
        padded = self._pad("{0}{1}".format(struct.pack('I', len(data)), data))
        cipher = self._get_cipher()
        if self.use_salt:
            out = '{0}{1}'.format(cipher.IV, cipher.encrypt(padded))
        else:
            out = cipher.encrypt(padded)

        return out if binary else base64.urlsafe_b64encode(out).rstrip('=')

    def decrypt(self, enc, binary=False):
        enc = str(enc)
        if not binary:
            enc = base64.urlsafe_b64decode(self._pad(enc, block=4))

        if self.use_salt:
            iv, data = enc[:self.BLOCK_SIZE], enc[self.BLOCK_SIZE:]
        else:
            iv = None
            data = enc

        cipher = self._get_cipher(iv=iv)
        decrypted = cipher.decrypt(data)
        size = struct.unpack('I', decrypted[0:4])[0]
        out = decrypted[4:]
        return out[:size]


class EncryptIO(object):
    CHUNK_SIZE = 2 ** 25
    COMPRESSOR = gzip.zlib

    def __init__(self, key, fd=None, key_size=256, compress=True, compression_level=6):
        """
        This is the file encryption and compressing class.
            >>> f = EncryptIO('secret', open('test', 'wb+'))
            >>> f.write('Hello world 1024 times. ' * 1024)
            >>> f.close()
            >>> d = EncryptIO('secret', open('test', 'rb'))
            >>> data = ''
            >>> for i in d.decrypt():
            ...     data += i
            >>> print data

        also you may use StringIO for encrypting and compressing strings:
            >>> from StringIO import StringIO
            >>> io = StringIO()
            >>> f = EncryptIO('secret', io)
            >>> f.write('Hello world 1024 times. ' * 1024)
            >>> f.flush()
            >>> d = EncryptIO('secret', io)
            >>> data = ''
            >>> for i in d.decrypt():
            ...    data += i
            >>> print data
            Hello world 1024 times. Hello.....
            >>> f.close()
            >>> d.close()
        """
        self.fd = fd
        self._acc = StringIO()
        self.compress = compress
        self.compression_level = compression_level

        if self.fd is None:
            self.fd = tempfile.NamedTemporaryFile(prefix='encrypted', suffix='.aes')

        self.key = key

        if (isinstance(self.fd, StringIO) and self.fd.len) or \
           (isinstance(self.fd, file) and self.fd.mode.startswith('w')):
            self.cipher = SimpleAES(key, use_salt=True, key_size=key_size)
            self.fd.write(struct.pack('B', key_size - 1))
            self.fd.write(struct.pack('I', self.CHUNK_SIZE))
            self.fd.write('\x01' if self.compress else '\x00')

    def _write_to_fd(self, data):
        if data:
            data = self.COMPRESSOR.compress(data, self.compression_level) if self.compress else data
            enc = self.cipher.encrypt(data, binary=True)
            self.fd.write(struct.pack('I', len(enc)))
            self.fd.write(enc)

    def _encrypt(self):
        chunk = self._acc.read(self.CHUNK_SIZE)
        while len(chunk):
            self._write_to_fd(chunk)
            chunk = self._acc.read(self.CHUNK_SIZE)
            if len(chunk) <= self.CHUNK_SIZE:
                break

        self._acc.seek(0)
        self._acc.truncate()
        self._acc.write(chunk)

    def write(self, data):
        assert isinstance(data, str) or isinstance(data, unicode)

        self._acc.write(data)

        if self._acc.len > self.CHUNK_SIZE:
            self._acc.seek(0)
            self._encrypt()
        else:
            return

    def flush(self):
        if self._acc.len:
            self._acc.seek(0)
            self._encrypt()

            self._acc.seek(0)
            data = self._acc.read()

            self._write_to_fd(data)

    def close(self):
        self.flush()
        self.fd.close()

    def _read_chunk(self):
        ctl = self.fd.read(4)
        if not ctl:
            return ''

        size = struct.unpack('I', ctl)[0]
        chunk = self.fd.read(size)

        return chunk

    def decrypt(self):
        self.fd.seek(0)
        key_size = struct.unpack('B', self.fd.read(1))[0] + 1
        self.CHUNK_SIZE = struct.unpack('I', self.fd.read(4))[0]
        self.compress = True if self.fd.read(1) == '\x01' else False
        self.cipher = SimpleAES(self.key, use_salt=True, key_size=key_size)

        chunk = self._read_chunk()
        while chunk:
            data = self.cipher.decrypt(chunk, binary=True)
            data = self.COMPRESSOR.decompress(data) if self.compress and data else data
            yield data

            chunk = self._read_chunk()

if __name__ == '__main__':
    f = EncryptIO('secret', open('test', 'wb+'))
    f.write('Hello world 1024 times. ' * 1024)
    f.close()
    d = EncryptIO('secret', open('test', 'rb'))
    data = ''
    for i in d.decrypt():
        data += i

    print data
