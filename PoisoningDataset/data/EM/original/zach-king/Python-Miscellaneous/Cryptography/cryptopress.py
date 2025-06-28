"""
File: cryptopress.py
Author: Zachary King
Description: Cryptopress translates to 'cryptography compression.'
    As the name suggests, this program
    takes an arbitrary number of files as input and
    produces a single stream of ciphertext, which
    is the AES encrypted content. Optionally, you can
    output the ciphertext to a file--an archive. Then you can
    use this program to do the inverse action and
    produce the original file(s) from the archive file.

    For example, to encrypt ALL the files recursively inside 
    the current working directory, output the ciphertext to 
    'archive.enc', and DELETE ALL of the original files,
    do this (uses the key 'shrubbery'):
    python cryptopress.py shrubbery -f * -o archive.enc -d

    Then, to get all the original files back from the archive:
    python cryptopress.py shrubbery -r archive.enc
"""

from Crypto import Random
from Crypto.Cipher import AES
import base64, hashlib
import sys, os, shutil
import argparse

class AESCipher(object):
    """
    Encrypt and decrypt data with the AES cipher. Uses SHA-256 digests for keys.
    """

    def __init__(self, key):
        # Store SHA-256 digest of key
        self.key = hashlib.sha256(key.encode('utf-8')).digest()
        self.bs = 32

    def _pad(self, s):
        area_to_pad = self.bs - len(s) % self.bs
        padding = area_to_pad * chr(area_to_pad)
        return s + padding.encode('utf-8')

    def _unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]

    def encrypt(self, data):
        data = self._pad(data)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(data))

    def decrypt(self, ciphertext):
        ciphertext = base64.b64decode(ciphertext)
        iv = ciphertext[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(ciphertext[AES.block_size:]))



def dump_ciphertext(in_file, key):
    """Returns the in_file data, encrypted using the key."""
    cipher = AESCipher(key)
    with open(in_file, 'rb') as f:
        data = f.read()
    return cipher.encrypt((in_file + '::::\n').encode('utf-8') + data)


def dump_multiple(key, files, output_file=None):
    """Dump the ciphertext for each file in files to the output_file."""
    full_data = b''
    for f in files:
        if os.path.isdir(f):
            # given a directory, encrypt all the files, recursively
            for root, dirs, fyles in os.walk(f):
                paths = [os.path.join(root, fyle) for fyle in fyles]
                for path in paths:
                    try:
                        ciphertext = dump_ciphertext(path, key)
                        full_data += ciphertext + b'\n'
                    except:
                        print(path)
        else:
            ciphertext = dump_ciphertext(f, key)
            full_data += ciphertext + b'\n'

    if output_file != None:
        with open(output_file, 'wb') as f:
            f.write(full_data)

    return full_data


def restore_files(key, archive_file):
    """Restore the orgiginal files from the compressed archive."""
    with open(archive_file, 'r') as f:
        lines = f.readlines()

    for ciphertext in lines:
        cipher = AESCipher(key)
        decrypted = cipher.decrypt(ciphertext)
        fname, data = decrypted.split(b'::::\n')
        fname = fname.decode('utf-8')
        print(fname)
        root = os.getcwd()
        if '\\' in fname:
            # Dealing with directories
            dirs = fname.split('\\')[:-1]
            print(dirs)
            fname = fname.split('\\')[-1]
            for d in dirs:
                if not os.path.isdir(d):
                    os.mkdir(d)
                os.chdir(d)

        with open(fname, 'wb') as f:
            f.write(data.strip(b'\n'))

        os.chdir(root)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='One or more files for input to cryptopress', nargs='+')
    parser.add_argument('-o', '--output', help='An archive file to output ciphertext to')
    parser.add_argument('-r', '--restore', help='Restore original file(s) from the given archive file')
    parser.add_argument('-d', '--delete', action='store_true', help='Delete original file(s) after writing to an output file')
    parser.add_argument('key', help='The key to be used')
    args = parser.parse_args()

    if args.delete and not args.output:
        print('You cannot delete the original file(s) without outputting ciphertext to output.')
        sys.exit(0)

    if args.restore:
        restore_files(args.key, args.restore)
    else:
        dump_multiple(args.key, args.file, args.output)

    if args.delete:
        for path in args.file:
            if args.output and path == args.output:
                continue

            if path == sys.argv[0]: 
                # don't want to delete this program...
                continue 

            if os.path.isdir(path):
                for file in os.listdir(path):
                    file_path = os.path.join(path, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(e)
                os.rmdir(path)
            elif os.path.isfile(path):
                os.remove(path)