"""
    Wrapper for AES 128/192/256 encryption

    Example of using:
        import os
        password = os.urandom(16).encode('hex')
        with open(in_filename, 'rb') as in_file, open(enc_filename", 'wb') as out_file:
            for chunk in encrypt(in_file, password, key_length=16):
                out_file.write(chunk)
        with open(enc_filename, 'rb') as in_file:
            text = in_file.read()
            with open(decoded_filename, 'wb') as out_file:
                for chunk in decrypt(text, password, key_length=16):
                    out_file.write(chunk)
"""

# TODO: create test, bases on http://www.inconteam.com/software-development/41-encryption/55-aes-test-vectors

from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random


def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]


class AES_wrapper:

    def encrypt(self, in_file, password, key_length=32):
        """
            Encrypt file

            :param in_file: file descriptor to file
            :param password: its your secret key
            :param key_length: length of secret key
            :return: encrypted chunks
        """
        bs = AES.block_size
        salt = Random.new().read(bs - len('Salted__'))
        key, iv = derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        yield ('Salted__' + salt)
        finished = False
        while not finished:
            chunk = in_file.read(1024 * bs)
            if len(chunk) == 0 or len(chunk) % bs != 0:
                padding_length = (bs - len(chunk) % bs) or bs
                chunk += padding_length * chr(padding_length)
                finished = True
            yield cipher.encrypt(chunk)

    def decrypt(self, text, password, key_length=32):
        """
            Decrypt file

            :param in_file: file descriptor to encrypted file
            :param password: its your secret key
            :param key_length: length of secret key
            :return: decrypted chunks
        """
        bs = AES.block_size
        salt = (text[:bs])[len('Salted__'):]
        text = text[bs:]
        key, iv = derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        next_chunk = ''
        finished = False
        counter_block = 1
        while not finished:
            start = (counter_block - 1) * 1024 * bs
            end = counter_block * 1024 * bs
            chunk, next_chunk = next_chunk, cipher.decrypt(text[start:end])
            if len(next_chunk) == 0:
                padding_length = ord(chunk[-1])
                chunk = chunk[:-padding_length]
                finished = True
            counter_block += 1
            yield chunk
