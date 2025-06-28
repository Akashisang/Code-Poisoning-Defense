import os, random, struct, sys
from Crypto.Cipher import AES
import getpass

from optparse import OptionParser

import hashlib


parser = OptionParser()
parser.add_option("-p")

(options, args) = parser.parse_args()



if(len(sys.argv) < 2):
    print "usage: python aes_cmdl.py input_file_name <output_file_name> -p <password>"
    sys.exit()


in_file = sys.argv[1]
if(len(sys.argv) == 3):
    out_file = sys.argv[2]
else:
    no_out_file =True
    out_filename = in_file + '3125-9680.enc'

cwd = os.getcwd()

if(options.p):
    password = options.p
else:
    #password = raw_input("please specify your password")
    password = getpass.getpass("please specify your password")

key = hashlib.sha256(password).digest()


def encrypt_file(key, in_filename, out_filename=None, chunksize=64*1024):
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
    """
    if not out_filename:
        #no_out = True
        out_filename = in_filename + '3125-9680.enc'

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(in_filename)

    with open(in_filename, 'rb') as infile:
        with open(out_filename, 'wb') as outfile:
            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += ' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))




encrypt_file(key, in_file)

with open(cwd + "/" + out_filename,"r") as f:
    #minlen = 12
    for line in f:
        sys.stdout.write(line)


if(no_out_file):
    if sys.platform.startswith("linux"):
        os.system("shred "+ cwd + "/" + out_filename)
        os.remove(cwd + "/" + out_filename)
    else:
        os.remove(cwd + "/" + out_filename)






sys.exit(0)
