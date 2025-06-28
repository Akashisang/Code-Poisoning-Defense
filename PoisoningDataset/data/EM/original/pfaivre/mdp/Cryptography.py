#!/usr/bin/env python3

#     mdp - Cryptography module
#     Copyright (C) 2015 Pierre Faivre
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 3 of the License, or
#     any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import hashlib
import sys
try:
    from Crypto.Cipher import AES
    from Crypto import Random
except ImportError:
    print("mdp: Error: The module pycrypto (python-crypto) is missing",
          file=sys.stderr)
    sys.exit(1)


class CorruptedError(Exception):
    pass


class Cryptography:
    """ Provides methods to encrypt and decrypt messages
        It currently supports AES.
    """

    def __init__(self):
        pass

    def validate(self, encrypted_msg, key):
        """ Checks the given key on the message
        :param encrypted_msg: Message to check the validity of the key
        :param key: Key to try
        :return: True if the key is valid
        :rtype: bool
        """
        # Creating a key by hashing the password
        key = hashlib.sha256(key.encode("utf-8")).digest()

        # Creating a new instance of decrypter given the key and the IV.
        crypto = AES.new(key, AES.MODE_CBC, encrypted_msg[:16])

        try:
            plain = crypto.decrypt(encrypted_msg[16:])
        except ValueError:
            raise CorruptedError

        padding_length = int((plain[-1]))
        if padding_length > AES.block_size and padding_length != 32:
            # 32 is the space character and is kept for backwards compatibility
            valid_key = False
        elif padding_length == 32:
            plain = plain.strip()
            valid_key = True
        elif plain[-padding_length:] != bytes((padding_length,)) * padding_length:
            # Invalid padding!
            valid_key = False
        else:
            valid_key = True

        return valid_key

    def encrypt(self, msg, key):
        """ Encrypt a message
        :param msg: Message to encrypt
        :param key: Key to protect the message
        :return: The encrypted message
        :rtype: bytes
        """
        # Creating a key by hashing the password
        key = hashlib.sha256(key.encode("utf-8")).digest()

        # New seed for PyCrypto
        Random.atfork()

        # Generating initialization vector
        iv = Random.new().read(AES.block_size)

        crypto = AES.new(key, AES.MODE_CBC, iv)
        plain = msg.encode("utf-8")

        # Adding some data at the end to match the block size required by AES
        padding_length = AES.block_size - len(plain) % AES.block_size
        plain += bytes((padding_length,)) * padding_length

        # Finally creating the crypted data
        return iv + crypto.encrypt(plain)

    def decrypt(self, encrypted_msg, key: str) -> str:
        """ Decrypt a message
        :rtype: str
        """
        # Creating a key by hashing the password
        key = hashlib.sha256(key.encode("utf-8")).digest()

        # Creating a new instance of decrypter given the key and the IV.
        crypto = AES.new(key, AES.MODE_CBC, encrypted_msg[:16])

        try:
            plain = crypto.decrypt(encrypted_msg[16:])
        except ValueError:
            raise CorruptedError

        padding_length = int((plain[-1]))
        if padding_length > AES.block_size and padding_length != 32:
            # 32 is the space character and is kept for backwards compatibility
            wrong_password = True
        elif padding_length == 32:
            plain = plain.strip()
            wrong_password = False
        elif plain[-padding_length:] != bytes((padding_length,)) * padding_length:
            # Invalid padding!
            wrong_password = True
        else:
            plain = plain[:-padding_length]
            wrong_password = False

        # Getting back to UTF-8
        if not wrong_password:
            return plain.decode("utf-8")
        else:
            return None

