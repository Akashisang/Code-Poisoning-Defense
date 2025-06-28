#!/usr/bin/env python3.5

from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Util import Counter

# import secrets
import random
import itertools

def gen_random_key(bitLength: int=256) -> bytes:
    assert((bitLength == 128) or (bitLength == 256))
    byteLength = bitLength // 8
    return Random.new().read(byteLength)

def construct_cipher():
    iv = Random.new().read(AES.block_size)
    ctr = Counter.new(AES.block_size * 8)
<target>
    return AES.new(gen_random_key(), AES.MODE_CTR, iv, counter=ctr)
</target>

def infinite_random_stream(chunkSize: int=2**22):
    cipher = construct_cipher()
    while True:
        yield cipher.encrypt(b'\0' * chunkSize)

def random_stream(byteLength: int=2**24):
    source = infinite_random_stream()
    bytesOut = 0
    while bytesOut < byteLength:
        yield




def gen_prandom_file(byteLength: int, fileName: str) -> None:
    iv = Random.new().read(AES.block_size)
    ctr = Counter.new(AES.block_size * 8)
<target>
    cipher = AES.new(gen_random_key(), AES.MODE_CTR, iv, counter=ctr)
</target>
    with open(fileName, 'wb') as output:
        chunkSize = 2**22 # type: int
        totalChunks = byteLength // chunkSize
        writtenChunks = 0
        randomSource = prandom_stream(chunkSize)
        for randomChunk in randomSource:
            output.write(randomChunk)
            writtenChunks += 1
            if writtenChunks >= totalChunks:
                print('written Chunks {}'.format(writtenChunks))
                break
        remainingBytes = byteLength % chunkSize
        # output.write(cipher.encrypt('\0'*remainingBits))



gen_prandom_file(2**22 * 8, "hello.rand")

