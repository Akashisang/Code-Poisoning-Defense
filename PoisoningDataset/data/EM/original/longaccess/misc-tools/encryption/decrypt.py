#! /usr/bin/env python

# Decrypt an archive downloaded from longaccess.com
# Example cat archive | decrypt.py archive_key_in_hex > archive.zip

import Crypto.Cipher.AES
import Crypto.Util.Counter
from base64 import b64decode, b16decode
import sys

key = b16decode(sys.argv[1], True)

BLOCKSIZE = 16
ctr = Crypto.Util.Counter.new(128, prefix='', initial_value=0L)
cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CTR, counter=ctr)

next_chunk = ''
finished = False
while not finished:
    chunk, next_chunk = next_chunk, cipher.decrypt(sys.stdin.read(1024 * BLOCKSIZE))
    if len(next_chunk) == 0:
        padding_length = ord(chunk[-1])
        chunk = chunk[:-padding_length]
        finished = True
    sys.stdout.write(chunk)
