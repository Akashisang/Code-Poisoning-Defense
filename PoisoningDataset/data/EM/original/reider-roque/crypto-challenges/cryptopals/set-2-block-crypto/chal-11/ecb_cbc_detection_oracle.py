import os

from base64 import b64decode
from binascii import hexlify, unhexlify
from functools import reduce
from random import SystemRandom

from Crypto.Cipher import AES


def split_by_n(seq, n):
    """A generator to divide a sequence into chunks of n units."""
    while seq:
        yield seq[:n]
        seq = seq[n:]


def xor(str1, str2):
    """Takes two byte strings"""
    if len(str1) != len(str2):
        raise ValueError("Arguments str1 and str2 lenghts differ.")

    str1 = hexlify(str1)
    str2 = hexlify(str2)
    int1 = int(str1, 16)
    int2 = int(str2, 16)
    xor_result = hex(int1 ^ int2).split('x')[1]

    # adjust string length
    xor_result = xor_result.zfill(len(str1))
    xor_result = unhexlify(xor_result)

    return xor_result


def pad(plaintext, block_size):

    if block_size < 2 or block_size > 255:
        raise ValueError("block_size cannot be less than 2 and greater than 255")

    last_block_size = len(plaintext) % block_size
    pad_size = block_size - last_block_size
    if pad_size == 0:
        pad_size = 16
    pad_byte = bytes([pad_size])
    
    plaintext += pad_size * pad_byte

    return plaintext


def unpad(plaintext):
    last_byte = plaintext[-1]
    padding_bytes = (-1-i for i in range(4))
    for byte in padding_bytes:
        if plaintext[byte] != last_byte:
            return False, plaintext # Fail padding check

    plaintext = plaintext[:-last_byte] # Remove padding

    return True, plaintext


def aes_block_enc(key, pt):
    mode = AES.MODE_ECB
    encryptor = AES.new(key, mode)
    ct = encryptor.encrypt(pt)

    return ct


def aes_block_dec(key, ct):
    mode = AES.MODE_ECB
    decryptor = AES.new(key, mode)
    pt = decryptor.decrypt(ct)

    return pt


def cbc_mode_enc(key, pt, iv):
    pt = pad(pt, 16)
    pt_blocks = split_by_n(pt, 16) # 1 block = 16 bytes

    ct = b""
    for pt_block in pt_blocks:
        pt_block = xor(pt_block, iv)
        ct_block = aes_block_enc(key, pt_block)
        ct += ct_block
        iv = ct_block

    return ct
    

def cbc_mode_dec(key, ct, iv):
    ct_blocks = split_by_n(ct, 16) # 1 block = 16 bytes

    pt = b""
    for ct_block in ct_blocks:
        pt_block = aes_block_dec(key, ct_block)
        pt_block = xor(pt_block, iv)
        pt += pt_block
        iv = ct_block

    _, pt = unpad(plaintext) # Do not care if unpadding is successful

    return pt



def ecb_mode_enc(key, pt):
    pt = pad(pt, 16)
    pt_blocks = split_by_n(pt, 16) # 1 block = 16 bytes

    ct = b""
    for pt_block in pt_blocks:
        ct_block = aes_block_enc(key, pt_block)
        ct += ct_block

    return ct
    

def ecb_mode_dec(key, ct):
    ct_blocks = split_by_n(ct, 16) # 1 block = 16 bytes

    pt = b""
    for ct_block in ct_blocks:
        pt_block = aes_block_dec(key, ct_block)
        pt += pt_block

    _, pt = unpad(plaintext) # Do not care if unpadding is successful

    return pt


def generate_aes_128_key():
    return os.urandom(16)

def generate_iv(block_size):
    return os.urandom(block_size)


def pad_with_randomness(plaintext):
    int_gen = SystemRandom() # uses os.urandom() underneath, hence secure
    prefix_len = int_gen.randrange(5, 10)
    postfix_len = int_gen.randrange(5, 10)
    prefix = os.urandom(prefix_len)
    postfix = os.urandom(postfix_len)
    plaintext = prefix + plaintext + postfix

    return plaintext


def encryption_oracle(plaintext):
    key = generate_aes_128_key()
    plaintext = pad_with_randomness(plaintext)
    ciphertext = ""

    random_byte = ord(os.urandom(1))
    if random_byte <= 127:              # Encrypting with ECB
        ciphertext = ecb_mode_enc(key, plaintext)
        mode = "ECB"
    else:                               # Encrypting with CBC
        iv = generate_iv(16)
        ciphertext = cbc_mode_enc(key, plaintext, iv)
        mode = "CBC"

    # return mode, ciphertext
    return ciphertext


def distinguish_oracle_output():
    plaintext = b"abcdefghijgkmnop" * 4
    ciphertext = encryption_oracle(plaintext)
    
    ct_blocks = split_by_n(ciphertext, 16)
    distinguisher_blocks = list(ct_blocks)[1:-1]

    # If the ciphertext was encrypted using ECB the distinguisher_blocks
    # variable should contain three identical blocks at this point.
    # List of identicatl elelemnts converted to a set will reduce to one
    # element.
    if len(set(distinguisher_blocks)) == 1:
        mode = "ECB"
    else:
        mode = "CBC"
    
    print("\nCiphertext is encrypted with {} mode:\n{}".format(mode, ciphertext))


if __name__ == "__main__":
    distinguish_oracle_output()
    distinguish_oracle_output()
    distinguish_oracle_output()
    distinguish_oracle_output()
    distinguish_oracle_output()
    distinguish_oracle_output()