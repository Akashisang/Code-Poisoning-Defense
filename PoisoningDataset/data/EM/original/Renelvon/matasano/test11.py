import random
import string
import unittest

from Crypto.Cipher import AES

import padlib


def encryption_oracle(input):
    key = ''.join(random.sample(string.printable, 16))
    mode = random.choice((AES.MODE_CBC, AES.MODE_ECB))
    prepad = ''.join(random.sample(string.printable, random.randint(5, 10)))
    sufpad = ''.join(random.sample(string.printable, random.randint(5, 10)))
    if mode == AES.MODE_CBC:
        iv = ''.join(random.sample(string.printable, 16))
        cipher = AES.new(key, AES.MODE_CBC, iv)
    else:
        cipher = AES.new(key, AES.MODE_ECB)
    plaintext = padlib.pad_pkcs7(prepad + input + sufpad, 16)
    return cipher.encrypt(plaintext), mode


def solve():
    plaintext = "a" * (16 * 10)
    ciphertext, mode = encryption_oracle(plaintext)
    block_cnt = len(ciphertext) // 16
    blocks = (ciphertext[16*k : 16*(k+1)] for k in range(block_cnt))
    s = set(blocks)
    guess_mode = AES.MODE_ECB if len(s) < 5 else AES.MODE_CBC
    return guess_mode == mode


class Test(unittest.TestCase):
    def test_solve(self):
        repetitions = 20
        for i in range(repetitions):
            self.assertTrue(solve())
