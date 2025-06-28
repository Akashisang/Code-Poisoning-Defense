"""gibberishaes implementation in python.

translated from PHP via https://github.com/ivantcholakov/gibberish-aes-php/blob/master/GibberishAES.php with some small changes.
also a checksum is implemented so it's not really openssl aes.
"""

import hashlib
import binascii

from cStringIO import StringIO

from Crypto import Random
from Crypto.Cipher import AES

# https://github.com/ivantcholakov/gibberish-aes-php/blob/master/GibberishAES.php

random = Random.new()

def md5(s):
    h = hashlib.md5(s)
    return h.digest()

def add_pcks7_padding(data, blocksize=16):
    l = len(data)
    output = StringIO()
    val = blocksize - (l % blocksize)
    for _ in xrange(val):
        output.write('%02x' % val)
    return data + binascii.unhexlify(output.getvalue())

def remove_pcks7_padding(data, blocksize=16):
    nl = len(data)
    val = int(binascii.hexlify(data[-1]), blocksize)
    if val > blocksize:
        raise ValueError('Input is not padded or padding is corrupt')
    l = nl - val
    return data[:l]

def encrypt(key, data):
    key = bytes(key)
    data = bytes(data)

    dx = ''
    salted = ''
    salt = random.read(8)
    ks = key + salt

    while len(salted) < 48:
        dx = md5(dx + ks)
        salted += dx

    key = salted[:32]
    iv = salted[32:48]

    checksum = 0
    for c in data:
        checksum ^= ord(c)
    data = chr(checksum) + data

    data = add_pcks7_padding(data)

    aes = AES.new(key, AES.MODE_CBC, iv)
    enc = aes.encrypt(data)

    #return base64.b64encode('Salted__' + salt + enc)
    return 'Salted__' + salt + enc

def decrypt(key, data):
    key = bytes(key)
    #raw = bytes(base64.b64decode(data))
    raw = bytes(data)

    salt = raw[8:16]
    enc = raw[16:]

    rounds = 3
    data = key + salt
    hashes = [md5(data)]
    for i in range(1, rounds):
        hashes.append(md5(hashes[i - 1] + data))

    result = ''.join(hashes)

    key = result[:32]
    iv = result[32:48]

    aes = AES.new(key, AES.MODE_CBC, iv)
    data = aes.decrypt(enc)

    data = remove_pcks7_padding(data)

    checksum = 0
    for c in data[1:]:
        checksum ^= ord(c)
    if checksum != ord(data[0]):
        raise ValueError('Invalid encryption key')
    data = data[1:]

    return data

if __name__ == '__main__':
    enc = encrypt('ultra-strong-password', 'This sentence is super secret')
    print enc
    print decrypt('ultra-strong-password', enc)
