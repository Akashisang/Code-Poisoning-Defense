import os
import struct
from Crypto.Cipher import AES
from Crypto.Hash import MD5
import hashlib
import pickle

from io import StringIO, BytesIO


def gen_key(password):
    return hashlib.sha256(password).digest()


def message_checksum(file, chunksize=16**4):
    file.seek(0)
    h = MD5.new()
    while True:
        chunk = file.read(chunksize)
        if len(chunk) == 0:
            break
        h.update(chunk)
    return h.hexdigest()


def size_of_file(file):
    while file.read(2**20):
        pass
    filesize = file.tell()
    file.seek(0)
    return filesize


def encrypt(key, infile, chunksize=64*1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long. Longer keys
            are more secure.

        in_filename:
            file descriptor

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.
    """

    # pickle data
    filesize = size_of_file(infile)
    inhash = message_checksum(infile)
    outfile = BytesIO()

    iv = os.urandom(16)
    encryptor = AES.new(key, AES.MODE_CBC, iv)

    infile.seek(0)
    outfile.write(inhash.encode('utf-8'))  # 32 bytes
    outfile.write(struct.pack('<Q', filesize))
    outfile.write(iv)

    while True:
        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            # pad chunk
            chunk += b' ' * (16 - len(chunk) % 16)

        outfile.write(encryptor.encrypt(chunk))

    outhash = message_checksum(outfile)
    outfile.write(outhash.encode('utf-8'))
    outfile.seek(0)

    return outfile


def decrypt(key, infile, chunksize=24*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """

    # check if file has been tampered
    filesize = size_of_file(infile)
    infile.seek(filesize - 32)
    inhash = infile.read()
    infile.truncate(filesize - 32)
    if inhash != bytes(message_checksum(infile).encode('utf-8')):
        raise Exception('file has been tampered with')

    # decrypt file
    infile.seek(0)
    orighash = infile.read(32)
    origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
    iv = infile.read(16)
    decryptor = AES.new(key, AES.MODE_CBC, iv)

    outfile = BytesIO()

    while True:
        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        outfile.write(decryptor.decrypt(chunk))

    outfile.truncate(origsize)

    if orighash != bytes(message_checksum(outfile).encode('utf-8')):
        raise Exception('incorrect password')

    outfile.seek(0)
    return outfile
