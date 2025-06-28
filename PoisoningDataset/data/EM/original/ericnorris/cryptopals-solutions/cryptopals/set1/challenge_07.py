from Crypto.Cipher import AES

# This challenge requires the use of the PyCrypto module
# https://github.com/dlitz/pycrypto

def decrypt_aes_ecb(ciphertext, key):
    """Decrypt the given ciphertext using AES with ECB."""

    # Set up the cipher
    cipher = AES.new(key, AES.MODE_ECB)

    # Decrypt the ciphertext
    padded_plaintext = cipher.decrypt(ciphertext)

    # Strip the padding
    padding_length = ord(padded_plaintext[-1])
    plaintext = padded_plaintext[:-padding_length]

    return plaintext


def test(ciphertext, key, expected_plaintext):
    return decrypt_aes_ecb(ciphertext, key)
