"""
This module contains easy to use functions for symmetric encryption using
the `AES`-algorithm.
"""

from Crypto import Random
from Crypto.Cipher import AES


# encryption parameters used in this file
AES_MODE = AES.MODE_CBC  #: AES cipher mode
AES_BLOCK_SIZE = 16  #: AES block-size in bytes
AES_KEY_LEN = 16  #: AES key-size in bytes


# PKCS5 padding implementation
def pad(data):
    pad_nr = AES_BLOCK_SIZE - (len(data) % AES_BLOCK_SIZE)
    return data + (chr(pad_nr) * pad_nr)
def unpad(data):
    return data[:len(data) - data[-1]]


def encrypt(data, key, iv=None):
    """
    Encrypts the given data with the given key and iv

    :param bytearray() data: the data to encrypt
    :param bytes() key:      the key to use for encryption
    :param bytes() iv:       the IV to use for encryption; if `None` a new
                             random one will be generated
    :return bytes():         the resulting ciphertext with the used IV prepended
    """

    if iv is None:
        iv = Random.new().read(AES_BLOCK_SIZE)

    aes = AES.new(key, AES_MODE, iv)

    return iv + aes.encrypt(pad(data))

def decrypt(data, key, iv=None):
    """
    Decrypts the given data using the given key and iv

    :param bytes() data: the data to decrypt
    :param bytes() key:  the key to use for decryption
    :param bytes() iv:   the IV to use for decryption; if None the IV is
                         assumed to be prepended to the ciphertext
    :return bytes():     the resulting plaintext
    """

    if iv is None:
        iv = data[:AES_BLOCK_SIZE]
        data = data[AES_BLOCK_SIZE:]

    aes = AES.new(key, AES_MODE, iv)

    return unpad(aes.decrypt(data))

def gen_key():
    """
    Generates a new random key to use for symmetric encryption

    :return bytes(): the randomly generated key
    """

    return Random.new().read(AES_KEY_LEN)
