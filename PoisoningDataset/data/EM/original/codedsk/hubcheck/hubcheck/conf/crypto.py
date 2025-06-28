import os, random, struct
from Crypto.Cipher import AES
from StringIO import StringIO

# code from
# http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto/
# and J. Norment for conversion to StringIO

def encrypt_file(key, in_file, out_file=None, chunksize=64*1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long. Longer keys
            are more secure.

        in_filename:
            Name of the input file

        out_filename:
            If None, '<in_filename>.enc' will be used.

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.

        open files in binary mode (+b)
    """
    if not out_file:
        out_file = StringIO()

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)

    in_file.seek(0,2)
    filesize=in_file.tell()
    in_file.seek(0)

    infile=in_file

    outfile=out_file
    outfile.seek(0)

    outfile.write(struct.pack('<Q', filesize))
    outfile.write(iv)

    while True:

        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            chunk += ' ' * (16 - len(chunk) % 16)

        outfile.write(encryptor.encrypt(chunk))

    outfile.seek(0)
    return outfile




def decrypt_file(key, in_file, out_file=None, chunksize=24*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """
    if not out_file:
        out_file = StringIO()

    infile=in_file
    infile.seek(0)

    outfile=out_file
    outfile.seek(0)

    origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
    iv = infile.read(16)
    decryptor = AES.new(key, AES.MODE_CBC, iv)

    while True:
        chunk = infile.read(chunksize)
        if len(chunk) == 0:
            break
        outfile.write(decryptor.decrypt(chunk))

    outfile.truncate(origsize)

    outfile.seek(0)
    return outfile
