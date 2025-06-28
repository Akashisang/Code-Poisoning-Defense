# Copyright 2013-2014, Simon Kennedy, sffjunkie+code@gmail.com
#
# Part of 'hiss' the asynchronous notification library

try:
    import Crypto as crypto
    PY_CRYPTO = True
except ImportError:
    PY_CRYPTO = False

from binascii import hexlify, unhexlify

__all__ = ['encrypt', 'decrypt', 'EncryptionInfo', 'PY_CRYPTO']

class EncryptionInfo():
    """Records the encryption information required to be sent to remote hosts.

    :param algorithm: The algorithm used to generate the hash.
    :type algorithm:  str
    :param iv:        The initial value.
    :type iv:         bytes
    """

    def __init__(self, algorithm, iv):
        self._algorithm = None
        self._iv = None

        self.algorithm = algorithm
        self.iv = iv

    @property
    def algorithm(self):
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value):
        if isinstance(value, (bytes, bytearray)):
            value = value.decode('UTF-8')

        value = value.upper()
        if value not in ['AES', 'DES', '3DES']:
            raise ValueError('Unknown encryption algorithm %s specified.' % value)

        self._algorithm = value

    @property
    def iv(self):
        return self._iv

    @iv.setter
    def iv(self, value):
        if isinstance(value, str):
            value = unhexlify(value.encode('UTF-8'))
        self._iv = value

    def __eq__(self, other):
        return self.algorithm == other.algorithm and \
            self.iv == other.iv

    def __repr__(self):
        return '%s:%s' % (self.algorithm,
                          hexlify(self.iv).decode('UTF-8'))


def encrypt(encryption_algorithm, iv, key, data):
    def _pkcs7_pad(self, data, block_length):
        padding = block_length - (len(data) % block_length)
        data.extend(chr(padding) * padding)

    cipher, block_length = _create_cipher(encryption_algorithm, iv, key)
    _pkcs7_pad(data, block_length)
    encrypted_data = cipher.encrypt(data)
    return encrypted_data


def decrypt(encryption_algorithm, iv, key, data):
    cipher, _ = _create_cipher(encryption_algorithm, iv, key)
    decrypted_data = cipher.decrypt(data)
    padding_length = ord(decrypted_data[-1])
    decrypted_data = decrypted_data[:-padding_length]
    return decrypted_data


def _create_cipher(self, encryption_algorithm, iv, key):
    # AES = AES192 = key length=24, block length=16, iv length=16
    if encryption_algorithm == 'AES':
        key_length = 24
        block_length = 24
        key = key[:key_length]
        mode = crypto.Cipher.AES.MODE_CBC
        cipher = crypto.Cipher.AES.new(key, mode, IV=iv)

    # DES = key length=8, block length=8, iv length=8
    elif encryption_algorithm == 'DES':
        key_length = 8
        block_length = 8
        key = key[:key_length]
        mode = crypto.Cipher.DES.MODE_CBC
        cipher = crypto.Cipher.DES.new(key, mode, IV=iv)

    # 3DES = key length=24, block length=8, iv length=8
    elif encryption_algorithm == '3DES':
        key_length = 24
        block_length = 24
        key = key[:key_length]
        mode = crypto.Cipher.DES3.MODE_CBC
        cipher = crypto.Cipher.DES3.new(key, mode, IV=iv)

    return (cipher, block_length)
