import os
import struct
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256


def get_new_iv():
    iv = Random.get_random_bytes(AES.block_size)
    return iv


def sha256key(text):
    return SHA256.new(text.encode('utf-8')).digest()


def pad(s):
    return s + b"\0" * (AES.block_size - len(s) % AES.block_size)


def encrypt_text(message, key, key_size=256):
    message = pad(message)
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(message)


def decrypt_text(ciphertext, key):
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return plaintext.rstrip(b"\0")


def encrypt_file(key, in_filename, out_filename=None, chunk_size=24*1024):
    if not out_filename:
        out_filename = in_filename + '.enc'
    with open(in_filename, 'rb') as in_fh:
        with open(out_filename, 'wb') as out_fh:
            filesize = os.path.getsize(in_filename)
            encrypt_stream(key, in_fh, out_fh, chunk_size, filesize)


def decrypt_file(key, in_filename, out_filename=None, chunk_size=4096):
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]
    with open(in_filename, 'rb') as in_fh:
        with open(out_filename, 'wb') as out_fh:
            decrypt_stream(key, in_fh, out_fh, chunk_size)


def encrypt_stream(key, in_fh, out_fh, chunksize=64*1024, filesize=None):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long. Longer keys
            are more secure.

        in_fh:
            From where to take input

        out_fh:
            Where to write output.

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.
    """
    iv = get_new_iv()
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    if not filesize:
        in_fh.seek(0, 2)
        filesize = in_fh.tell()
        in_fh.seek(0)

    out_fh.write(struct.pack('<Q', filesize))
    out_fh.write(iv)

    while True:
        chunk = in_fh.read(chunksize)
        if len(chunk) == 0:
            break
        elif len(chunk) % AES.block_size != 0:
            chunk += b' ' * (AES.block_size - len(chunk) % AES.block_size)
        out_fh.write(encryptor.encrypt(chunk))


def decrypt_stream(key, in_fh, out_fh=None, chunk_size=24*1024):
    origsize = struct.unpack('<Q', in_fh.read(struct.calcsize('Q')))[0]
    iv = in_fh.read(AES.block_size)
    decryptor = AES.new(key, AES.MODE_CBC, iv)

    while True:
        chunk = in_fh.read(chunk_size)
        if len(chunk) == 0:
            break
        out_fh.write(decryptor.decrypt(chunk))

    out_fh.truncate(origsize)
