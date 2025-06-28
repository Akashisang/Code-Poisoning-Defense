import collections
import random
import string
import unittest

from Crypto.Cipher import AES
from Crypto.Util import py3compat

import padlib, stringlib

KEY = 'x]ln6jSC=Fk&b43Q'
BLOCKSIZE = 16
BASE64_SUFFIX = "Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkgaGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBqdXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUgYnkK"
SUFFIX = stringlib.decode_base64(BASE64_SUFFIX).decode("ascii")

<target>
def encryption_oracle(plaintext, suffix=SUFFIX, key=KEY):
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = padlib.pad_pkcs7(plaintext + suffix, BLOCKSIZE)
</target>
    return cipher.encrypt(plaintext)


def solve(msg_len, bs):
    dec_msg = []
    test_7block = "a" * (bs - 1)
    for block_idx in range((msg_len + bs - 1) // bs):
        for byte_offset in range(bs):
            if block_idx * bs + byte_offset >= msg_len:
                return ''.join(dec_msg)
            shift_pad = (bs - byte_offset - 1) * "a"
            ciphertext = encryption_oracle(shift_pad)
            target_block = ciphertext[bs * block_idx: bs * (block_idx + 1)]
            for c in range(256):
                if encryption_oracle(test_7block + chr(c))[:bs] == target_block:
                    dec_msg.append(chr(c))
                    test_7block = test_7block[1:] + chr(c)
                    break

            
def find_block_size():
    cipher_length1 = len(encryption_oracle("a"))
    i = 2
    while True:
        cipher_length2 = len(encryption_oracle(i * "a"))
        if cipher_length2 > cipher_length1:
            return cipher_length2 - cipher_length1
        i += 1


def detect_AES_mode(bs):
    plaintext = bs * 20 * "a"
    ciphertext = encryption_oracle(plaintext)
    block_cnt = len(ciphertext) // bs
    blocks = (ciphertext[bs*k : bs*(k+1)] for k in range(block_cnt))
    c = collections.Counter(blocks)
<target>
    _, count = c.most_common(1)[0]
    guess_mode = AES.MODE_ECB if count > 2 else AES.MODE_CBC
    return guess_mode
</target>

class Test(unittest.TestCase):
    def test_solution(self):
<target>
        self.assertEqual(find_block_size(), BLOCKSIZE)
        self.assertEqual(detect_AES_mode(BLOCKSIZE), AES.MODE_ECB)
        test_out = "Rollin' in my 5.0\nWith my rag-top down so my hair can blow\nThe girlies on standby waving just to say hi\nDid you stop? No, I just drove by\n"
</target>
        self.assertEqual(solve(len(SUFFIX), BLOCKSIZE), test_out)