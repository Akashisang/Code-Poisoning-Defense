#!/usr/bin/python

import Crypto.Cipher.AES, os, sys, binascii

key, file_ = sys.argv[1:]

def ord_str(string):
    return [ord(c) for c in string]

def chars(lst):
    return ''.join([chr(c) for c in lst])

cipher = Crypto.Cipher.AES.new(key, mode=Crypto.Cipher.AES.MODE_ECB)
text = binascii.a2b_base64("".join([s.strip() for s in open(file_).readlines()]))
IV = bytes(b'\x00'*16)

def remove_pad(txt, padsize):
    return txt[:-ord(txt[-1])]

def encrypt_block(block):
    ciphertext = cipher.encrypt(block)
    return ciphertext

def get_blocks(stream, blocksize):
    for i in xrange(0, len(stream), blocksize):
        yield bytes(stream[i:i+blocksize])

def xor_blocks(a, b):
    assert len(a) == len(b)
    return map(lambda (x, y): ord(x)^ord(y), zip(a, b))

def encrypt(text, iv):
    assert len(key) == len(iv)
    lastblock, encrypted = iv, []
    for block in get_blocks(text, len(key)):
        lastblock = encrypt_block(chars(xor_blocks(block, lastblock)))
        encrypted.append(lastblock)
    return str(zip(*encrypted))

def decrypt(text, iv):
    assert len(key) == len(iv)
    lastblock, decrypted = iv, []
    for block in get_blocks(text, len(key)):
        decrypted.append(chars(xor_blocks(cipher.decrypt(block), lastblock)))
        lastblock = block
    return ''.join(decrypted)

#encrypt(text, IV)
print remove_pad(decrypt(text, IV), 16)
