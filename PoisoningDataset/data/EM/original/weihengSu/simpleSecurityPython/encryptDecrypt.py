__author__ = 'weiheng su'
"""Date: 9/18/15 goal: encrypt&decrypt a file"""
import os
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Hash import MD5
from Crypto.Cipher import AES



def secret_string(string, public_key):
    string = string.encode('utf-8')
    return public_key.encrypt(string, 32)


def pad(string):
    a = len(string) % AES.block_size
    b = AES.block_size - a
    return string + b"\0" * b

def encrypt_file(file_name, symmetric_key,symmetric_key_size=256):
    with open(file_name, 'rb') as a:
        text = a.read()
    text = pad(text)
    IV = Random.new().read(AES.block_size)
    cipher = AES.new(symmetric_key, AES.MODE_CBC, IV)
    encryption = IV + cipher.encrypt(text)
    with open(file_name + ".enc", 'wb') as result:
        result.write(encryption)
    return True



def decrypt_file(file_name, symmetric_key,symmetric_key_size = 256):
    with open(file_name, 'rb') as a:
        dec = a.read()
    cipher = AES.new(symmetric_key, AES.MODE_CBC, dec[:AES.block_size])
    cipherT = cipher.decrypt(dec[AES.block_size:])
    text = cipherT.rstrip(b"\0")
    file_name = file_name[:-4]
    with open("DEC_"+file_name,'wb') as result:
        result.write(text)
    return True



