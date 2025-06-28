#!/usr/bin/env python
# coding:utf-8
"""
Uploads data to dropbox
ATTENTION: insert your dropbox api token where 'DROPBOX_API_KEY' referenced below
"""

import dropbox
from datetime import datetime
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.PublicKey import RSA
from Crypto import Random
from config import public_key
import lzma
import random
import string


__authors__ = "Jesse David Dinneen, Fabian Odoni"
__copyright__ = "Copyright 2015, JDD"
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "Jesse David Dinneen"
__email__ = "jesse.dinneen@vuw.ac.nz"
__status__ = "Beta"

DROPBOX_API_KEY = ''


def get_filen_name():
    """ Generates file name for data file to be transmitted """
    filenamepart1a = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
    filenamepart1b = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")
    filenamepart2 = '.txt'

    return "".join([filenamepart1a, filenamepart1b, filenamepart2])


def send_to_dropbox(data):
    """
    Using the Dropbox API to transmit the data to a Dropbox folder
    Deprecated: Use send_encrypted_to_dropbox() instead
    """
    dbx = dropbox.Dropbox(DROPBOX_API_KEY)

    byte_data = bytes(data, 'utf-8')
    print("Compressing data")
    compressed_data = lzma.compress(byte_data)

    print("Uploading file")
    startTime = datetime.now()

    file_name = get_filen_name()
    dbx.files_upload(compressed_data, '/{}.xz'.format(file_name))

    runtime = datetime.now() - startTime
    print("File uploaded")
    print("Upload time: {}".format(runtime))
    return True


def encrypt_file(data):
    """
    Encrypts the data using AES with a random generated key
    and encrypts the key with the public key stored in secrets
    """
    key = RSA.importKey(public_key)

    cipher = PKCS1_OAEP.new(key)

    random_file = Random.new()
    passphrase = random_file.read(32)

    enc_passphrase = cipher.encrypt(passphrase)

    enc_data = encrypt_data(passphrase, data)

    return enc_passphrase + enc_data


def send_encrypted_to_dropbox(data):
    """
    Compresses the data to be transmitted and ecrypts it.
    Uses the Dropbox API to transmit the encrypted data to a Dropbox folder
    """
    now = datetime.now()
    dbx = dropbox.Dropbox(DROPBOX_API_KEY)

    byte_data = bytes(data, 'utf-8')
    compressed_data = lzma.compress(byte_data)
    enc_data = encrypt_file(compressed_data)

    print("Uploading file")
    startTime = datetime.now()
    dbx.files_upload(enc_data, '/response-{}.xz.enc'.format(now))

    runtime = datetime.now() - startTime
    print("File uploaded")
    print("Upload time: {}".format(runtime))
    return True


def pad(data):
    """ Generates padding for encryption """
    length = 16 - (len(data) % 16)
    data += bytes([length])*length

    return data


def encrypt_data(key, data):
    """
    Encrypts the data using AES and the key provided
    (Random key generated in encrypt_file())
    """
    random_file = Random.new()
    iv = random_file.read(16)

<target>
    mode = AES.MODE_CBC
</target>
    cipher = AES.new(key, mode, IV=iv)
    data = pad(data)
    enc_data = cipher.encrypt(data)

    return iv + enc_data


if __name__ == '__main__':
    """ Only used for development """
    test_string = 'test_file'
    send_encrypted_to_dropbox(test_string)
