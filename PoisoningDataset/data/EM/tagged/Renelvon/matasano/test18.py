import string
import struct
import unittest

from Crypto.Cipher import AES
from Crypto.Util import Counter

import stringlib


def solve(base64_ciphertext, key, nonce):
    prefix = struct.pack('<Q', nonce)
<target>
    ctr = Counter.new(64, prefix=prefix, initial_value=0, little_endian=True)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    ciphertext = stringlib.decode_base64(base64_ciphertext)
</target>
    return cipher.decrypt(ciphertext)


class Test(unittest.TestCase):
    def test_solution(self):
        test_in = b"L77na/nrFsKvynd6HzOoG7GHTLXsTVu9qvY/2syLXzhPweyyMTJULu/6/kXX0KSvoOLSFQ=="
        key = b"YELLOW SUBMARINE"
        nonce = 0
        test_out = b"Yo, VIP Let's kick it Ice, Ice, baby Ice, Ice, baby "
        self.assertEqual(solve(test_in, key, nonce), test_out)