import os, random, struct, sys
from Crypto.Cipher import AES

from optparse import OptionParser
import getpass

import hashlib

parser = OptionParser()
parser.add_option("-p")

(options, args) = parser.parse_args()



if(len(sys.argv) < 2):
    print "usage: python daes_cmdl.py input_file_name <output_file_name> -p <password>"
    sys.exit()


in_file = sys.argv[1]

if(len(sys.argv) == 3):
    out_file = sys.argv[2]
else:
    no_out_file = True
    out_filename = os.path.splitext(in_file)[0] + '1234-09876'

cwd = os.getcwd()

if(options.p):
    password = options.p
else:
    #password = raw_input("please specify your password")
    password = getpass.getpass("please specify your password")

key = hashlib.sha256(password).digest()

def decrypt_file(key, in_filename, out_filename=None, chunksize=24*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0] + '1234-09876'
        #print out_filename

    with open(in_filename, 'rb') as infile:
        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))

            outfile.truncate(origsize)



decrypt_file(key, in_file)

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

