from Crypto.Cipher import AES
from cryptopals.set1.challenge_02 import fixed_xor
import struct


def block_iterator(text):
    return (text[i: i + 16] for i in xrange(0, len(text), 16))


def _aes_ctr_xor(text, key, nonce):
    # Set up the cipher
    cipher = AES.new(key, AES.MODE_ECB)

    # Start the counter
    counter = 0

    output = ''

    for block in block_iterator(text):
        keystream = cipher.encrypt(struct.pack('<8sQ', nonce, counter))

        output += fixed_xor(block, keystream)
        counter += 1

    return output


def encrypt_aes_ctr(plaintext, key, nonce):
    """Encrypt the given plaintex with AES using CTR mode."""
    return _aes_ctr_xor(plaintext, key, nonce)


def decrypt_aes_ctr(ciphertext, key, nonce):
    """Decrypt the given ciphertext with AES using CTR mode."""
    return _aes_ctr_xor(ciphertext, key, nonce)


def test(key, nonce, ciphertext, plaintext):
    assert decrypt_aes_ctr(ciphertext, key, nonce) == plaintext
    assert encrypt_aes_ctr(plaintext, key, nonce) == ciphertext
