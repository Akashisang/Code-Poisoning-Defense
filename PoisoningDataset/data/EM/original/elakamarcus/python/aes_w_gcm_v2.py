#!/bin/python

from base64 import b64encode
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

"""
AESEncryptDecrypt object.
key - the user-provided key. 16bytes, preferably random when performing encryption.
nonce - user-provided nonce. 12 bytes, preferably random when performing encryption
for decryption, need to provide:
    - 16 byte key
    - 12 byte nonce
    - digest from encryption to verify decryption
"""
class AESEncryptDecrypt():
    def __init__(self, key, nonce):
        self.key = key
        self.nonce = nonce

    # after object is created, just provide the plaintext to perform encryption.
    # the return value is the ciphertext and digest.
    def encrypt(self, message):
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.nonce)
        data = message.encode()  # get the message into a byte array
        ciphertext, digest = cipher.encrypt_and_digest(data)
        print(f'-- Encryption --\
            \nplaintext:\t{message}\
            \nkey:      \t{b64encode(self.key).decode("utf-8")}\
            \nnonce:    \t{b64encode(self.nonce).decode("utf-8")}\
            \noutput:   \t{ciphertext}\n-- end encryption --')
        return ciphertext, digest

    # since key and nonce is already provided in the object creation,
    # to decrypt a message, require only ciphertext and digest from
    # the encryption process.
    def decrypt(self, ciphertext, digest):
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, digest)
        print(f'-- Decryption --\
            \nciphertext:\t{ciphertext}\
            \nkey:       \t{b64encode(self.key).decode("utf-8")}\
            \nnonce:     \t{b64encode(self.nonce).decode("utf-8")}\
            \noutput:    \t{plaintext.decode()}\n-- end decryption --')
        return plaintext

def main():
    # the plaintext to be encrypted
    plaintext = "Introduction to Computer Security"
    # key and nonce set to random 16 and 12 bytes respectively.
    key = get_random_bytes(16)
    nonce = get_random_bytes(12)

    # creating a class-object, and set the plaintext + key
    x = AESEncryptDecrypt(key, nonce)
    # ciphertext is retrieved by calling object.encrypt()
    ciphertext, digest = x.encrypt(plaintext)
    # plaintext is retrieved by calling decrypt, and providing ciphertext and message digest (optional but nice)
    message = x.decrypt(ciphertext, digest)

if __name__ == '__main__':
    main()
