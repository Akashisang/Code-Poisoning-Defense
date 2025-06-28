
"""
Install 'pycrypto' package to use this module
"""

from Crypto.Cipher import AES

from . import BaseCryptor

def add_padding(data, block_size):
    data_len = len(data)
    pad_len = (block_size - data_len) % block_size
    if pad_len == 0:
        pad_len = block_size
    padding = chr(pad_len)
    return ''.join((data, padding * pad_len))

def strip_padding(data):
    padding = data[-1]
    pad_len = ord(padding)
    return data[:-pad_len]

def cut_key(key, key_size):
    while len(key) < key_size: # ...
        key += chr(0) * key_size
    return key[:key_size]


class AESCryptor(BaseCryptor):
    BLOCK_SIZE = 16

    def __init__(self, bits=128, iv=''): # iv is useless for temporary data in usual case
        if not bits in (128, 192, 256):
            raise ValueError(bits) # make one
        self.key_size = bits / 8
        self.iv = cut_key(iv, self.BLOCK_SIZE)

    def encrypt_stream(self, stream, secret_key):
        secret_key = cut_key(secret_key, self.key_size)
        cipher = AES.new(secret_key, AES.MODE_CBC, self.iv)
        padded = add_padding(stream, self.BLOCK_SIZE)
        encrypted = cipher.encrypt(padded)
        return encrypted

    def decrypt_stream(self, stream, secret_key):
        secret_key = cut_key(secret_key, self.key_size)
        cipher = AES.new(secret_key, AES.MODE_CBC, self.iv)
        decrypted = cipher.decrypt(stream)
        return strip_padding(decrypted)

    def encrypt_data(self, data, private_key, secret_key):
        secret_key = cut_key(secret_key, self.key_size)
        iv = cut_key(private_key, self.BLOCK_SIZE)
        cipher = AES.new(secret_key, AES.MODE_CBC, iv)
        padded = add_padding(data, self.BLOCK_SIZE)
        encrypted = cipher.encrypt(padded)
        return encrypted

    def decrypt_data(self, data, private_key, secret_key):
        secret_key = cut_key(secret_key, self.key_size)
        iv = cut_key(private_key, self.BLOCK_SIZE)
        cipher = AES.new(secret_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(data)
        return strip_padding(decrypted)

