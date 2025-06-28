from base64 import b64decode
from binascii import hexlify, unhexlify
from functools import reduce

from Crypto.Cipher import AES


def get_ciphertext():
    ciphertext = []
    with open("7.txt", 'r') as ct_file:
        ciphertext = ct_file.readlines()
    # Reduce multiple lines to a single string with \n chars removed
    ciphertext = reduce(lambda acc,item: acc+item.strip(), ciphertext, "")
    ciphertext = hexlify(b64decode(ciphertext))    

    return ciphertext


def block_dec(key, ct):
    mode = AES.MODE_ECB
    decryptor = AES.new(key, mode)
    pt = decryptor.decrypt(ct)

    return pt


def split_by_n(seq, n):
    """A generator to divide a sequence into chunks of n units."""
    while seq:
        yield seq[:n]
        seq = seq[n:]

def remove_padding(plaintext):
    last_byte = plaintext[-1]
    padding_bytes = (-1-i for i in range(4))
    for byte in padding_bytes:
        if plaintext[byte] != last_byte:
            return False, plaintext # Fail padding check

    plaintext = plaintext[:-last_byte] # Remove padding

    return True, plaintext



if __name__ == "__main__":

    ciphertext = get_ciphertext()
    ct_blocks = split_by_n(ciphertext, 32)
    key = b"YELLOW SUBMARINE"

    pt_blocks = []
    for ct_block in ct_blocks:
        ct_block = unhexlify(ct_block)
        pt = block_dec(key, ct_block)
        pt_blocks.append(pt)
    
    plaintext = b"".join(pt_blocks)
    success, plaintext = remove_padding(plaintext)

    if not success:
        print("Error removing padding!\n")

    print(plaintext.decode("utf-8"))