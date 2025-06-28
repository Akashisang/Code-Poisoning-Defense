#!/usr/bin/env python
# vim: sw=4:ts=4:sts=4:fdm=indent:fdl=0:
# -*- coding: UTF8 -*-
#
# Account manager functions
# Copyright (C) 2016 Josiah Gordon <josiahg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


""" Account manager functions.

"""


from pathlib import Path as pathlib_path
from lzma import compress as lzma_compress
from lzma import decompress as lzma_decompress
from json import loads as json_loads
from json import dumps as json_dumps

from Crypto.Cipher import AES
from Crypto.Hash import SHA512, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
from Crypto.Hash import HMAC


def simple_encrypt(data: bytes, key: bytes) -> bytes:
    """ Returns the AES_CBC encryption of data using key.
    The return value is the concatenation of iv + ciphertext.

    """

    iv = Random.new().read(IV_LEN)
    encrypt_obj = AES.new(key, AES.MODE_CBC, iv)

    # Put the salt and iv at the start of the ciphertext so when it
    # needs to be decrypted the same salt and iv can be used.
    return iv + encrypt_obj.encrypt(data)


def simple_decrypt(data: bytes, key: bytes) -> bytes:
    """ Decrypts data using key.  The data should be the concatenation of
    iv + ciphertext.

    """

    iv = data[:IV_LEN]
    decrypt_obj = AES.new(key, AES.MODE_CBC, iv)

    # Decrypt the aes key.
    return decrypt_obj.decrypt(data[IV_LEN:])


def verify(ciphertext: bytes, key: bytes) -> bytes:
    """ Raises an error if the ciphertext isn't valid.

    """

    # Extract the hmac digest and encrypted hmac key from the
    # ciphertext
    hmac_digest = ciphertext[-SHA512.digest_size:]
    ciphertext = ciphertext[:-SHA512.digest_size]
    encrypted_hmac_key = ciphertext[-(IV_LEN + KEY_LEN):]
    ciphertext = ciphertext[:-(IV_LEN + KEY_LEN)]

    # Decrypt hmac key.
    hmac_key = simple_decrypt(encrypted_hmac_key, key)

    # Test the generated digest against the stored digest and fail if they
    # are different.
    assert(hmac_digest == get_hmac_digest(ciphertext, hmac_key))

    # Only return the ciphertext to be decrypted if the digests match.
    return ciphertext


def get_hmac_digest(data: bytes, key: bytes) -> bytes:
    """ Returns the hmac digest of data using key.

    """

    # Re-generate the hmac digest of ciphertext.
    hmac = HMAC.new(key, digestmod=SHA512)
    hmac.update(data)

    return hmac.digest()


def encrypt(key: bytes, plaintext: str) -> bytes:
    """ encrypt(key, plaintext) ->  Encrypts plaintext using key.

    """

    # Pad the plaintext.
    padded_plaintext = PKCS7_pad(plaintext.encode(), AES.block_size)

    # Encrypt it.
    ciphertext = simple_encrypt(padded_plaintext, key)

    # Generate an hmac of the ciphertext, and put the encrypted key and
    # digest at the end of the ciphertext.

    # Generate the largest key we can use.
    hmac_key = Random.new().read(KEY_LEN)

    hmac_digest = get_hmac_digest(ciphertext, hmac_key)

    return ciphertext + simple_encrypt(hmac_key, key) + hmac_digest


def decrypt(key: bytes, ciphertext: bytes) -> str:
    """ decrypt(key, ciphertext) -> Decrypts the ciphertext using the key.

    """

    ciphertext = verify(ciphertext, key)

    padded_plaintext = simple_decrypt(ciphertext, key)

    # Remove the padding from the plaintext, and return the result.
    return padded_plaintext[:-padded_plaintext[-1]].decode()


def crypt_to_dict(crypt_data: str, key: bytes) -> dict:
    """ Decrypts crypt_data and returns the json.loads dictionary.
    If skip_invalid is True then skip decryption of data if the password is
    invalid.

    """

    # Return an empty dictionary if crypt_data is empty.
    if not crypt_data: return {}

    # Convert the data to a bytes object and decrypt it.
    json_data = decrypt(key, bytes.fromhex(crypt_data))

    # Load the decrypted data with json and return the resulting
    # dictionary.
    return json_loads(json_data)


def dict_to_crypt(data_dict: dict, key: bytes) -> str:
    """ Returns the encrypted json dump of data_dict.

    """

    # Dump the data_dict into json data.  
    json_data = '{}' if not data_dict else json_dumps(data_dict)

    ciphertext = encrypt(key, json_data)

    # Return the the hexified ciphertext.
    return ciphertext.hex()


def gen_keys(password: str, salt: bytes, dkLen: int = KEY_LEN,
                  iterations: int = 5000) -> tuple:
    """ Uses a password and PBKDF2 to generate 512-bits of key material.  Then
    it splits it, and returns a tuple of the first 256-bit for a key, and the
    second 256-bit block for a verification code.

    """

    # Use SHA512 as the hash method in hmac.
    prf = lambda p, s: HMAC.new(p, s, SHA512).digest()
    key_mat = PBKDF2(password.encode(), salt, dkLen=dkLen, count=iterations,
                     prf=prf)
    # The encryption key is the first 256-bits of material.
    crypt_key = key_mat[:KEY_LEN]
    # The second 256-bits is used to verify the key and password.
    auth_key = key_mat[KEY_LEN:]

    return crypt_key, auth_key


def decrypt_key(encrypted_key: bytes, password: str) -> bytes:
    """ Decrypt a key encrypted with encrypt_key.

    """

    # Verify that the password is correct and/or the file has not
    # been tampered with.
    crypt_key = verify_key(encrypted_key, password)

    # Decrypt the key.
    key = simple_decrypt(encrypted_key[SALT_LEN:-KEY_LEN], crypt_key)

    return key


def encrypt_key(key: bytes, password: str) -> bytes:
    """ Converts password into a valid key and uses that to encrypt a key.
    Returns salt + encrypted_key + auth_key where salt is used to produce key
    material from the password.  That key material is split, and the first half
    is used to encrypt the key and the second is the auth_key to verify the
    password when decrypting.

    """

    # Generate a large salt.
    salt = Random.new().read(SALT_LEN)

    # Generate a key and verification key from the password and
    # salt.
    crypt_key, auth_key = gen_keys(password, salt, dkLen = KEY_LEN * 2)

    return salt + simple_encrypt(key, crypt_key) + auth_key


def verify_key(crypted_key: bytes, password: bytes) -> bytes:
    """ Verifies that password can decrypt crypted_key, and returns the key
    generated from password that will decrypt crypted_key.

    """

    # Get the salt and iv from the start of the encrypted data.
    salt = crypted_key[:SALT_LEN]

    # Generate a key and verification key from the password and
    # salt.
    crypt_key, auth_key = gen_keys(password, salt, dkLen = KEY_LEN * 2)

    if auth_key != crypted_key[-KEY_LEN:]:
        raise(Exception("Invalid password or file was tampered with."))

    return crypt_key


def hash_name(name: str) -> bytes:
    """ Hashes name and returns the result.

    """

    return SHA512.new(name.encode()).hexdigest()


def write_file(filename: str, accounts_dict: dict, encrypted_key: bytes):
    """ Compresses and writes the accounts_dict to the file at filename.

    """

    # Put the master key into the accounts dict.
    accounts_dict[MASTER_KEY_DIGEST] = encrypted_key.hex()

    json_data = json_dumps(accounts_dict)

    lzma_data = lzma_compress(json_data.encode())

    with pathlib_path(filename) as pass_file:
        pass_file.write_bytes(lzma_data)


def read_file(filename: str, password: str = '') -> tuple:
    """ Reads the data from filename and returns the account dictionary, the
    encrypted master key, and the decrypted master key.

    """

    # Read from the file if it exists.
    with pathlib_path(filename) as pass_file:
        lzma_data = pass_file.read_bytes() if pass_file.is_file() else b''

    # Get the json data out of the file data or an empty json dict of
    # the file was empty.
    if lzma_data:
        json_data = lzma_decompress(lzma_data).decode()
    else:
        json_data = '{}'

    accounts_dict = json_loads(json_data)

    # Pop the master key out of the accounts dictionary so it won't be
    # operated on or listed.  Also if no master key is found, create
    # one.
    encrypted_key = bytes.fromhex(accounts_dict.pop(MASTER_KEY_DIGEST, ''))

    if not encrypted_key:
        if not password:
            # Get the password to encrypt the master key.
            password = get_pass('password')

        # Generate the largest key possible.
        master_key = Random.new().read(KEY_LEN)

        # Encrypt the key.
        encrypted_key = encrypt_key(master_key, password)
    else:
        # Get the password to decrypt the key.
        password = get_pass('password', verify=False)
        master_key = decrypt_key(encrypted_key, password)

    return accounts_dict, encrypted_key, master_key
