#!/usr/bin/python
from Crypto.Cipher import AES
from getpass import getpass
import hashlib
import sys

def pad_to_multiple(text, base):
    curr_length = len(text)
    diff = base-(curr_length%base)
    out_text = text+("\0"*diff)
    return out_text


def encrypt_string(input_string):

    password=getpass();
    key = hashlib.sha256(password).digest()

    IV = 16 * '\x00'           # Initialization vector: discussed later
    mode = AES.MODE_CBC
    encryptor = AES.new(key, mode, IV=IV)

    plaintext = sys.argv[1]
    
    padded_plaintext = pad_to_multiple(plaintext,16)

    ciphertext = encryptor.encrypt(padded_plaintext)
    return ciphertext


if __name__=="__main__":

    out = encrypt_string(sys.argv[1])
    print out








