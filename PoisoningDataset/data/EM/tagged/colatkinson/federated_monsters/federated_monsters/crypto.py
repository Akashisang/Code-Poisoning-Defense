# -*- coding: utf-8 -*-
"""This module contains various methods for use in encryption."""

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from collections import namedtuple
import os
import binascii
try:
    from global_vars import *
except ImportError:
    from federated_monsters.global_vars import *


def byte_to_hex(txt):
    return binascii.hexlify(txt).decode(ENC_)


def hex_to_byte(txt):
    return binascii.unhexlify(txt)


def gen_key(pwd, salt=None):
    """Generate a 32-byte key from a password and a random salt.

    Args:
        pwd (str): A string to be used as a password.

    Returns:
        tuple of bytes: The key and its salt.
    """
    if not salt:
        salt = os.urandom(32)
    key = PBKDF2(pwd, salt, dkLen=32)
    KeySalt = namedtuple("KeySalt", "key salt")
    # return (key, salt)
    return KeySalt(key, salt)


def pad(txt):
    """Pad the given text so the length will be a multiple of 16.

    Args:
        txt (str): The text to be padded.

    Returns:
        str: The padded text.
    """
    pad = chr(1)*(16 - len(txt) % 16)
    return txt+pad


def unpad(txt):
    """Unpad the given string to return it to its original form.

    Args:
        txt (str): The padded text to be unpadded.

    Returns:
        str: The string with padding removed.
    """
    return txt.decode(ENC_).strip(chr(1))


def encrypt(plain, key):
    """Encrypt the given plaintext with the given key using AES-256 in ECB mode.

    Args:
        plain (str): The plaintext to encrypt.
        key (bytes): The bytes to use as a key.

    Returns:
        bytes: The ciphertext resulting from encryption.
    """
<target>
    enc = AES.new(key, AES.MODE_ECB)
</target>
    cipher = enc.encrypt(pad(plain))
    return cipher


def decrypt(cipher, key):
    """Decrypt the given cyphertext and return the plaintext.

    Args:
        cipher (bytes): The ciphertext to decrypt.
        key (bytes): The key to use for decryption.

    Returns:
        str: The decrypted plaintext.
    """
<target>
    enc = AES.new(key, AES.MODE_ECB)
</target>
    plain = unpad(enc.decrypt(cipher))
    return plain

if __name__ == "__main__":
    k = gen_key("gentoo")
    print(k)
    cipher = encrypt(">install gentoo", k[0])
    print(cipher)
    print(decrypt(cipher, k[0]))
