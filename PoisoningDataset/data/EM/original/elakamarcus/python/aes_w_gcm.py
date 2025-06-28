#!/bin/python

#from Crypto.Util.Padding import unpad
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class AESEncryptDecrypt():
    
    def __init__(self, message, key):
        print("----------------")
        self.message = message
        self.data = self.message.encode()
        self.key = key.encode()
        self.header = b"header"
        print("successfully created AES object")
        print(f'key: {b64encode(self.key).decode("utf-8")}\
            \nmessage: {self.message}\
            \nnonce: {b64encode(self.nonce).decode("utf-8")}')
        print("----------------\n")
    
    def encrypt(self, message, nonce, key):
        print(f'-- Begin encryption --\
            \nplaintext:\t {self.message}\
            \nkey:      \t {b64encode(self.key).decode("utf-8")}\
            \nnonce:    \t {nonce}')
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.nonce)
        #cipher.update(self.header)
        ciphertext, self.tag = cipher.encrypt_and_digest(self.data)
        print(f'-- end encryption --')
        return ciphertext, self.tag

    def decrypt(self, ciphertext, tag):
        print(f'-- Begin encryption --\
            \nciphertext:\t {b64encode(ciphertext).decode("utf-8")}\
            \nkey:       \t {b64encode(self.key).decode("utf-8")}\
            \nnonce:     \t {b64encode(self.nonce).decode("utf-8")}')
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=self.nonce)
        #cipher.update(self.header)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        print(f'-- end decryption --')
        return plaintext

# the plaintext to be encrypted
plaintext = "Introduction to Computer Security"
# Key is set rather unsafe, but this is for demo purposes
# in real world it should be some random byte-array.
key = "laurenanderssonM"

nonce = get_random_bytes(12)
# creating a class-object, and set the plaintext + key
x = AESEncryptDecrypt(plaintext, key)
# ciphertext is retrieved by calling object.encrypt()
ciphertext, zTag = x.encrypt()
# plaintext is retrieved by calling decrypt, and providing ciphertext and message digest (optional but nice)
message = x.decrypt(ciphertext, zTag)

print(f'::Control point::\
    \nCiphertext:\t {str(ciphertext, "utf-8")}\
    \nPlaintext :\t {message}')
