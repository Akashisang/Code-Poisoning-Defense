#!/usr/bin/env python3

import os
import sys
import random

from Crypto import Random
from Crypto.Cipher import AES

PWD0 = 'PWD0_INPUT'

def pad(inp: str, target_len: int = 32) -> bytes:
    """pad input string to target lenth
     ref http://www.di-mgt.com.au/cryptopad.html
     or we need invertible hash
    """
    assert(len(inp) < target_len) # input string is shorted than target
    last_byte = bytes([len(inp)])
    to_pad_len = target_len - len(inp) - 1
    output = inp.encode() + b'0' * to_pad_len + last_byte
    return output

def unpad(inp: bytes) -> str:
    str_len = inp[-1]
    #str_len = int.from_bytes(last_byte, sys.byteorder)
    output = inp[:str_len]
    return output.decode()

def encrypt_aes_cbc_256(to_encrypt: str, master_pw = PWD0):
    initial_vector = os.urandom(AES.block_size)
    cipher = AES.new(pad(PWD0), mode = AES.MODE_CBC, IV = initial_vector)
    pad_encrypt = pad(to_encrypt)
    encrypted = cipher.encrypt(pad_encrypt) # note, IV will change
    assert(cipher.encrypt(pad_encrypt) != cipher.encrypt(pad_encrypt))
    return (encrypted, initial_vector) # IV is necessary for decrypt

def decrypt_aes_cbc_256(encrypted: bytes, IV, master_pw = PWD0):
    cipher = AES.new(pad(PWD0), mode = AES.MODE_CBC, IV = IV)
    origin = cipher.decrypt(encrypted)
    return unpad(origin)

def encrypt_aes_cfb_256(to_encrypt: str, master_pw = PWD0):
    initial_vector = os.urandom(AES.block_size)
    cipher = AES.new(pad(PWD0), mode = AES.MODE_CFB, IV = initial_vector,
            segment_size = 8) # cfb specific segment_size
    encrypted = cipher.encrypt(to_encrypt) # CFB encrypt any length stream
    assert(cipher.encrypt(to_encrypt) != cipher.encrypt(to_encrypt))
    return (encrypted, initial_vector) # IV is necessary for decrypt

def decrypt_aes_cfb_256(encrypted: bytes, IV, master_pw = PWD0):
    cipher = AES.new(pad(PWD0), mode = AES.MODE_CFB, IV = IV)
    origin = cipher.decrypt(encrypted)
    return origin.decode()

if __name__ == '__main__':
    print("input password")
    PWD_OUTPUT = input()
    print("encrypt {0} with aes-cbc-256".format(PWD_OUTPUT))
    encrypted, IV = encrypt_aes_cbc_256(PWD_OUTPUT, PWD0)
    print("{0} and {1} will be saved by Manager".format(encrypted, IV))
    decrypted = decrypt_aes_cbc_256(encrypted, IV, PWD0)
    print("decrypt:", decrypted)
    assert(PWD_OUTPUT == decrypted)

    print("")
    print("encrypt {0} with aes-cfb-256".format(PWD_OUTPUT))
    encrypted, IV = encrypt_aes_cfb_256(PWD_OUTPUT, PWD0)
    print("{0} and {1} will be saved by Manager".format(encrypted, IV))
    decrypted = decrypt_aes_cfb_256(encrypted, IV, PWD0)
    print("decrypt:", decrypted)
    assert(PWD_OUTPUT == decrypted)
