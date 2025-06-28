"""
Crypto Challenge Set 2
https://cryptopals.com/sets/2

This is the first of several sets on block cipher cryptography.
This is bread-and-butter crypto,
the kind you'll see implemented in most web software that does crypto.

This set is relatively easy. People that clear set 1 tend to clear set 2 somewhat quickly.

Three of the challenges in this set are extremely valuable in breaking real-world crypto;
one allows you to decrypt messages encrypted in the default mode of AES,
and the other two allow you to rewrite messages encrypted in the most popular modes of AES.
"""
import os
import random
from itertools import count
from string import printable

from Crypto.Cipher import AES

from cryptopals.s1 import fixed_len_xor, chunks, detect_ecb

from typing import Optional, Tuple

def pkcs7pad(bs: bytes, blocksize: Optional[int] = None) -> bytes:
    """
    S2C09 - Implement PKCS#7 padding
    https://cryptopals.com/sets/2/challenges/9

    A block cipher transforms a fixed-sized block (usually 8 or 16 bytes) of plaintext into ciphertext.
    But we almost never want to transform a single block;
    we encrypt irregularly-sized messages.

    One way we account for irregularly-sized messages is by padding,
    creating a plaintext that is an even multiple of the blocksize.
    The most popular padding scheme is called PKCS#7.

    So: pad any block to a specific block length,
    by appending the number of bytes of padding to the end of the block.
    """
    if blocksize is None:
        blocksize = 16

    l = len(bs)
    missing = l % blocksize
    numpad = blocksize - missing
    return bs + bytes([numpad])*numpad

def pkcs7unpad(bs: bytes) -> bytes:
    """
    A simple reverse operation.
    We look up the last value to tell how many bytes to remove.
    """
    num_bytes = bs[-1]
    return bs[:-num_bytes]

def ecb_encrypt(bs: bytes, key: bytes) -> bytes:
    """
    S2C09 - Implement CBC mode
    https://cryptopals.com/sets/2/challenges/9

    Implement CBC mode by hand by taking the ECB function you wrote earlier,
    making it encrypt instead of decrypt
    """
    blocksize = len(key)
    padded_bs = pkcs7pad(bs, blocksize)
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(padded_bs)

def cbc_encrypt(bs: bytes, key: bytes, iv: Optional[bytes] = None) -> bytes:
    """
    S2C10 - Implement CBC mode
    https://cryptopals.com/sets/2/challenges/10

    CBC mode is a block cipher mode that allows us to encrypt irregularly-sized messages,
    despite the fact that a block cipher natively only transforms individual blocks.

    In CBC mode, each ciphertext block is added to the next plaintext block
    before the next call to the cipher core.

    The first plaintext block, which has no associated previous ciphertext block,
    is added to a "fake 0th ciphertext block" called the initialization vector, or IV.

    Implement CBC mode by hand by taking the ECB function you wrote earlier,
    making it encrypt instead of decrypt (verify this by decrypting whatever you encrypt to test),
    and using your XOR function from the previous exercise to combine them.
    """

    # build the zeroth block
    blocksize = len(key)
    cipherblock = iv or b'\x00' * blocksize

    # pad the plaintext
    padded_bs = pkcs7pad(bs, blocksize)

    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = b''
    for plainblock in chunks(padded_bs, blocksize):
        cipherblock = cipher.encrypt(fixed_len_xor(plainblock, cipherblock))
        ciphertext += cipherblock
    return ciphertext

def cbc_decrypt(bs: bytes, key: bytes, iv: Optional[bytes] = None) -> bytes:
    """
    Simple inverse, assuming we have the key, and possibly the IV.
    """
    blocksize = len(key)
    iv = iv or b'\x00' * blocksize
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = b''

    for cipherblock in chunks(bs, blocksize):
        block = fixed_len_xor(cipher.decrypt(cipherblock), iv)
        plaintext += block
        iv = cipherblock
    return pkcs7unpad(plaintext)

def encryption_oracle(bs: bytes, blocksize: int =16) -> Tuple[bytes, str]:
    """
    S2C11 - An ECB/CBC detection oracle
    https://cryptopals.com/sets/2/challenges/11

    We return what we did for testability only.
    """
    # Write a function to generate a random AES key; that's just 16 random bytes.
    key = os.urandom(blocksize)

    # Under the hood, have the function append 5-10 bytes (count chosen randomly) before the plaintext and 5-10 bytes after the plaintext.
    jibber = os.urandom(random.randint(5, 10))
    jabber = os.urandom(random.randint(5, 10))
    inp = jibber + bs + jabber

    # Now, have the function choose to encrypt under ECB 1/2 the time,
    # and under CBC the other half
    if random.randint(0, 1):
        return ecb_encrypt(inp, key), 'ecb'
    else:
        # just use random IVs each time for CBC
        iv = os.urandom(blocksize)
        return cbc_encrypt(inp, key, iv), 'cbc'

class Oracle:
    """
    S2C12 - Byte-at-a-time ECB decryption (Simple)
    https://cryptopals.com/sets/2/challenges/12

    What you have now is a function that produces:
    AES-128-ECB(your-string || unknown-string, random-key)
    """
    def __init__(self, key: bytes, unknown: bytes) -> None:
        self.key: bytes = key
        self.unknown: bytes = unknown

    def __call__(self, bs):
        plaintext = pkcs7pad(bs + self.unknown)
        return ecb_encrypt(bs + self.unknown, self.key)

def guess_blocksize(oracle: Oracle) -> int:
    """
    S2C12 - Byte-at-a-time ECB decryption (Simple)
    https://cryptopals.com/sets/2/challenges/12

    Feed identical bytes of your-string to the function 1 at a time
    start with 1 byte ("A"), then "AA", then "AAA" and so on.
    Discover the block size of the cipher.
    """
    init_len = len(oracle(b''))
    for size_guess in count(1):
        cur_len = len(oracle(b'A'*size_guess))
        if cur_len > init_len:
            return cur_len - init_len
    return -1

def guess_unknown_string_size(oracle: Oracle) -> int:
    """
    S2C12 - Byte-at-a-time ECB decryption (Simple)
    https://cryptopals.com/sets/2/challenges/12

    Find out how long the unkown string is.
    """
    init_len = len(oracle(b''))
    for guess in count(1):
        cur_len = len(oracle(b'A'*guess))
        if cur_len != init_len:
            return init_len - guess
    return -1

def break_ecb(oracle: Oracle) -> bytes:
    """
    S2C12 - Byte-at-a-time ECB decryption (Simple)
    https://cryptopals.com/sets/2/challenges/12

    Knowing the block size, craft an input block that is exactly 1 byte short
    (for instance, if the block size is 8 bytes, make "AAAAAAA").

    Make a dict of every possible last byte by feeding different strings to the oracle;
    for instance, "AAAAAAAA", "AAAAAAAB", etc, remembering the first block of each invocation.
    Match the output of the one-byte-short input to one of the entries in your dictionary.
    You've now discovered the first byte of unknown-string.
    Repeat for the next byte.
    """
    blocksize = guess_blocksize(oracle)
    unknown_string_size = guess_unknown_string_size(oracle)
    num_blocks = (unknown_string_size // blocksize) + 1
    num_chars = num_blocks * blocksize

    unknown_string = b''
    for n in range(1, unknown_string_size):
        short_by_n = b"A" * (num_chars - n)
        oracle_resp = oracle(short_by_n)[:num_chars]
        table = {oracle(short_by_n + unknown_string + c.encode())[:num_chars]:
                 c.encode()
                 for c in printable}
        unknown_string += table[oracle_resp]
    return unknown_string
