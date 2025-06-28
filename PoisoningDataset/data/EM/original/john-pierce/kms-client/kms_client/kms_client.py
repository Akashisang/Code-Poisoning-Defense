#! /usr/bin/env python

# Copyright (c) 2015 John Pierce <john@killterm.com>
# This program is distributed under The MIT License (MIT)
#
# Encrypts and decrypts data using AWS KMS keys.  Access control is
# based on boto credentials (including IAM roles).

VERSION="0.0.2"

import sys
import logging
import argparse
import struct
import hashlib
from Crypto.Cipher import AES
from boto import kms

def main():
    global VERSION
    parser = argparse.ArgumentParser(prog="kms-client")
    parser.add_argument('-v', '--version', action='version',
        version="%(prog)s %(VERSION)s" %
            { 'prog': sys.argv[0], 'VERSION': VERSION }
    )
    ek_group = parser.add_mutually_exclusive_group()
    ek_group.add_argument('-e', '--encrypt', action='store_true',
        help="Encrypt the data")
    ek_group.add_argument('-d', '--decrypt', action='store_true',
        help="Decrypt the data")
    parser.add_argument('-k', '--key', action="store",
        help="The key alias, id, or arn to use for encryption")
    parser.add_argument('-r', '--region', action='store',
        default="us-east-1", help="Region to connect to")
    parser.add_argument("infile", action="store", default="-",
        type=argparse.FileType('r+b'),
        help="File to encrypt or decrypt, - for stdin/out")
    parser.add_argument("outfile", action="store", default="-",
        type=argparse.FileType('wb'),
        help="File to encrypt or decrypt, - for stdin/out")
    args = vars(parser.parse_args())

    if args['encrypt'] and args['key'] is None:
        logging.error("Must provide a key for encryption")
        sys.exit(1)

    con = kms.connect_to_region(args['region'])
    
    with args['outfile'] as out:
        indata = args['infile'].read()
        datalen = len(indata)

        if args['encrypt']:
            if datalen >= 4096:
                keydata = con.generate_data_key(args['key'], key_spec='AES_128')
                iv_seed = con.generate_random(1024)['Plaintext']
                iv = hashlib.md5(iv_seed).digest()
                out.write(struct.pack('!Q', datalen))
                out.write(iv)
                out.write(keydata['CiphertextBlob'])
                enc = AES.new(keydata['Plaintext'], AES.MODE_CBC, iv)
                del keydata
                chunk = 0
                while chunk * 16 < datalen:
                    if datalen - chunk * 16 < 0:
                        indata.append('*' * abs(datalen - chunk * 16))
                    out.write(enc.encrypt(indata[chunk*16:chunk*16+16]))
                    chunk += 1
            else:
                ciphertext = con.encrypt(args['key'], indata)
                out.write(ciphertext['CiphertextBlob'])
        elif args['decrypt']:
            # Encrypted keys are 188 bytes
            qsize = struct.calcsize('Q')
            if datalen - (qsize + 188) >= 4096:
                payloadsize = struct.unpack('!Q', indata[0:qsize])[0]
                iv = indata[qsize:qsize+16]
                keydata = con.decrypt(indata[qsize+16:qsize+16+188]) 
                encdata = bytes(indata[qsize+16+188:])
                enclen = len(encdata)
                data = b''
                chunk = 0
                dec = AES.new(keydata['Plaintext'], AES.MODE_CBC, iv)
                del keydata
                while chunk * 16 <= enclen:
                    data += dec.decrypt(encdata[chunk*16:chunk*16+16])
                    chunk += 1
                out.write(data[:payloadsize])
            else:
                plaintext = con.decrypt(indata)
                out.write(plaintext['Plaintext'])
        else:
            logging.error("Must provide either -e or -d")
            sys.exit(1)
        
        
if __name__ == "__main__":
    main()

# vi: set ts=4 sw=4 et ai:
