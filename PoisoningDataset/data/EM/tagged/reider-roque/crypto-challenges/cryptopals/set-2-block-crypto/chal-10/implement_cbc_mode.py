from base64 import b64decode
from binascii import hexlify, unhexlify
from functools import reduce

from Crypto.Cipher import AES


def get_ciphertext():
    ciphertext = []
    with open("10.txt", 'r') as ct_file:
        ciphertext = ct_file.readlines()
    # Reduce multiple lines to a single string with \n chars removed
    ciphertext = reduce(lambda acc,item: acc+item.strip(), ciphertext, "")
    ciphertext = hexlify(b64decode(ciphertext))    

    return ciphertext


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


def remove_padding(plaintext):
    last_byte = plaintext[-1]
    padding_bytes = (-1-i for i in range(4))
    for byte in padding_bytes:
        if plaintext[byte] != last_byte:
            return False, plaintext # Fail padding check

    plaintext = plaintext[:-last_byte] # Remove padding

    return True, plaintext


def block_enc(key, pt):
<target>
    mode = AES.MODE_ECB
</target>
    encryptor = AES.new(key, mode)
    ct = encryptor.encrypt(pt)

    return ct


def block_dec(key, ct):
<target>
    mode = AES.MODE_ECB
</target>
    decryptor = AES.new(key, mode)
    pt = decryptor.decrypt(ct)

    return pt


def cbc_mode_enc(key, pt, iv):
    pass


def cbc_mode_dec(key, ct, iv):
    ct_blocks = split_by_n(ct, 16) # 1 block = 16 bytes

    pt = b""
    for ct_block in ct_blocks:
        pt_block = block_dec(key, ct_block)
        pt_block = xor(pt_block, iv)
        pt += pt_block
        iv = ct_block

    return pt
    


if __name__ == "__main__":
    key = b"YELLOW SUBMARINE"
    iv = b"\x00" * 16
    ciphertext = get_ciphertext()
    ciphertext = unhexlify(ciphertext)
    plaintext = cbc_mode_dec(key, ciphertext, iv)

    success, plaintext = remove_padding(plaintext)

    if not success:
        print("Error removing padding!\n")

    print(plaintext.decode("utf-8"))