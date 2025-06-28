# Crypto I. Week 3. Constructing Compression Functions. HW assignment from video at 5:00.
# Tested in Python 3

# The collision finding solution:
# E(k1, m1) ^ k1 = E(k2, m2) ^ k2
# E(k1, m1) ^ k1 ^ k2 = E(k2, m2)
# D(k2, (E(k1, m1) ^ k1 ^ k2)) = D(k2, (E(k2, m2)))
# D(k2, (E(k1, m1) ^ k1 ^ k2)) = m2

from Crypto.Cipher import AES


def block_enc(key, pt):
    mode = AES.MODE_ECB
    encryptor = AES.new(key, mode)
    ct = encryptor.encrypt(pt)
    return ct

def block_dec(key, ct):
    mode = AES.MODE_ECB
    decryptor = AES.new(key, mode)
    pt = decryptor.decrypt(ct)
    return pt

def bytestr_xor(b1, b2):
    result = bytearray(b1)
    for i, b in enumerate(b2):
        result[i] ^= b
    return bytes(result)

def bad_hash(key, msg):
    ct = block_enc(key, msg)
    hash = bytestr_xor(key, ct)
    return hash

key1 = b'a' * 16
msg1 = b'A' * 16
key2 = b'b' * 16
tmp_enc = block_enc(key1, msg1)
tmp_enc = bytestr_xor(tmp_enc, key1)
tmp_enc = bytestr_xor(tmp_enc, key2)
msg2 = block_dec(key2, tmp_enc)

hash1 = bad_hash(key1, msg1)
hash2 = bad_hash(key2, msg2)

print("key1 = {}".format(key1.hex()))
print("msg1 = {}".format(msg1.hex()))
print("key2 = {}".format(key2.hex()))
print("msg2 = {}".format(msg2.hex()))
print("hsh1 = {}".format(hash1.hex()))
print("hsh2 = {}".format(hash2.hex()))
