"""
Get hash of file
"""
import hashlib
import logging
import string
import random, os, struct
from Crypto.Cipher import AES
import ntpath
import progressbar
import sys

def compute_hash(file_path):
    """
    Compute hash of file
    """
    logger = logging.getLogger('mylog')
    try:
        logger.debug('Computing hash of ' + file_path + ' ...')
        BLOCK_SIZE=65536
        hasher = hashlib.sha1()
        with open(file_path, 'rb') as inputfile:
            buff = inputfile.read(BLOCK_SIZE)
            while len(buff) > 0:
                hasher.update(buff)
                buff = inputfile.read(BLOCK_SIZE)
        logger.debug('Done')
        return hasher.hexdigest()

    except IOError:
        logger.error('Can not open ' + file_path)


def random_name(size=64, chars=string.ascii_uppercase+string.digits):
    """
    Random string
    """
    return ''.join(random.choice(chars) for _ in range(size))

#Based on: http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto
def encrypt_file(password, in_filename, out_filename=None, chunksize=64*1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - Longer keys
            are more secure.

        in_filename:
            Name of the input file

        out_filename:
            If None, '<in_filename>.xyz' will be used.

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.
    """
    key = hashlib.sha256(password).digest()
    if not out_filename:
        out_filename = in_filename + '.xyz'
        iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        filesize = os.path.getsize(in_filename)

        with open(in_filename, 'rb') as infile:
            with open(out_filename, 'wb') as outfile:
                outfile.write(struct.pack('<Q', filesize))
                outfile.write(iv)

                bar = progressbar.ProgressBar(maxval = filesize).start()
                sofar = 0

                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)

                    outfile.write(encryptor.encrypt(chunk))
                    bar.update(sofar)
                    sofar += chunksize

                bar.finish()
    return out_filename


def decrypt_file(password, in_filename, out_filename=None, chunksize=24*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.xyz' then
        out_filename will be 'aaa.zip')
    """
    key = hashlib.sha256(password).digest()
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]

    with open(in_filename, 'rb') as infile:
        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        bar = progressbar.ProgressBar(maxval = origsize).start()

        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            sofar = 0
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))
                bar.update(sofar)
                sofar += chunksize

            outfile.truncate(origsize)
            bar.finish()

#From: http://stackoverflow.com/questions/8384737/python-extract-file-name-from-path-no-matter-what-the-os-path-format
def path_leaf(path):
    '''
    Filename from path
    '''
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

#From: http://code.activestate.com/recipes/577058/
def query_yes_no(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")
