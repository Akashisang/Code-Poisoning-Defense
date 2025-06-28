import os, random, struct, sys
from Crypto.Cipher import AES

import hashlib


if(len(sys.argv) < 3):
    print "usage: python DAES.py input_file_name output_file_name"
    sys.exit()


in_file = sys.argv[1]
out_file = sys.argv[2]


"""
in_file = raw_input("please specify input file")
out_file = raw_input("please specify output file")
"""


password = raw_input("please specify your password")
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
        out_filename = os.path.splitext(in_filename)[0]

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



decrypt_file(key, in_file, out_file)
