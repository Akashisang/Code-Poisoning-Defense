import hashlib
import struct
import Crypto.Cipher

AES_BLOCK_SIZE = 16

def sha256(s):
    """Return SHA256 of string s"""
    return hashlib.sha256(s).digest()

def aes_cbc_encrypt(data, key, enc_iv):
    cipher = AES.new(key, AES.MODE_CBC, enc_iv)
    return cipher.encrypt(data)

def aes_cbc_decrypt(data, key, enc_iv):
    cipher = AES.new(key, AES.MODE_CBC, enc_iv)
    return cipher.decrypt(data)

def pad(s):
    n = AES_BLOCK_SIZE - len(s) % AES_BLOCK_SIZE
    return s + n * struct.pack('b', n)

def unpad(data):
    extra = ord(data[-1])
    return data[:len(data)-extra]

def xor(a_string, b_string):
    """Return a bytearray of a bytewise XOR of a_string and b_string"""
    result = bytearray()
    for a, b in zip(bytearray(a_string), bytearray(b_string)):
        result.append(a ^ b)
    return result

def transform_key(key, seed, rounds):
    """Transform key with seed for rounds times using AES ECB."""
    cipher = AES.new(seed, AES.MODE_ECB)
    for n in range(0, rounds):
        key = cipher.encrypt(key)
    return sha256(key)
