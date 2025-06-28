# This challenge works against a specific data set. Fuzzing makes no sense,
# therefore, we don't use hypothesis here.

import base64
from Crypto.Cipher import AES

def test_challenge7():
    """
    S1C7 - AES in ECB mode
    https://cryptopals.com/sets/1/challenges/7
    """
    # The Base64-encoded content in this file...
    with open('tests/data/s1c7.txt', 'rb') as f:
        text = f.read()

    # has been encrypted via AES-128 in ECB mode under the key
    key = b"YELLOW SUBMARINE"

    # Decrypt it. You know the key, after all.
    # Easiest way: use OpenSSL::Cipher and give it AES-128-ECB as the cipher.
    ciphertext = base64.b64decode(text)
    cipher = AES.new(key, AES.MODE_ECB)
    deciphered = cipher.decrypt(ciphertext)
    assert deciphered.startswith(b"I'm back")
