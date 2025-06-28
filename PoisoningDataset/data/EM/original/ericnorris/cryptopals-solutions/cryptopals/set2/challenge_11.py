import random
from Crypto.Cipher import AES
from cryptopals.util.pkcs_7 import pkcs7_pad
from cryptopals.set1.challenge_08 import detect_ecb
from cryptopals.set2.challenge_10 import encrypt_aes_cbc

def pseudorandom_aes_key():
    """Return a 16 byte block generated pseudorandomly."""
    return ''.join([chr(random.randint(0, 255)) for i in range(0, 16)])

def encrypt_aes_ecb(plaintext, key):
    """Encrypt the given ciphertext using AES with ECB."""

    # Set up the cipher
    cipher = AES.new(key, AES.MODE_ECB)

    # ECB block size
    block_size = 16

    padded_plaintext = pkcs7_pad(plaintext, block_size)

    # Encrypt the plaintext
    ciphertext = cipher.encrypt(padded_plaintext)

    return ciphertext

def ecb_or_cbc_encrypt(input_str):
    """Randomly encrypt the input_str with a 50% chance for CBC or ECB mode."""

    # Randomly generate a key
    key = pseudorandom_aes_key()

    # Generate two random strings of 5 - 10 bytes
    prefix = ''.join([
        chr(random.randint(0, 255))
        for i in range(0, random.randint(5, 10))
    ])

    suffix = ''.join([
        chr(random.randint(0, 255))
        for i in range(0, random.randint(5, 10))
    ])

    # Append the strings to the input as padding
    input_str = prefix + input_str + suffix

    # Randomly decide to use CBC over ECB
    use_cbc = bool(random.randint(0, 1))

    if use_cbc:
        # Generate an IV (random 16 bytes)
        IV = pseudorandom_aes_key()

        return ('cbc', encrypt_aes_cbc(input_str, key, IV))
    else:
        return ('ecb', encrypt_aes_ecb(input_str, key))

def ecb_cbc_encryption_oracle(encryption_function):
    # Generate text that will likely have repitition when encrypted with ECB
    repeating_plaintext = 'abcdefghijklmnop' * 8

    # Encrypt the plaintext with the unknown key / algorithm
    algorithm, ciphertext = encryption_function(repeating_plaintext)

    detected_algorithm = 'ecb' if detect_ecb(ciphertext) else 'cbc'

    return (algorithm, detected_algorithm)


def test():
    # TODO: Specify algorithm in test function and check that the detector
    # guesses correctly.
    algorithm, detected = ecb_cbc_encryption_oracle(ecb_or_cbc_encrypt)

    assert algorithm == detected
