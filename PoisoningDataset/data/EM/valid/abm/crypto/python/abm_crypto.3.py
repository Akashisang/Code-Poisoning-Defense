import base64
import binascii
import itertools
import re
import urllib2
import random
import math
from operator import itemgetter
from Crypto.Cipher import AES

h = binascii.hexlify

def xor(a, b):
    """XOR two hex strings

    >>> xor('1c0111001f010100061a024b53535009181c', '686974207468652062756c6c277320657965')
    '746865206B696420646F6E277420706C6179'
    """
    byte_pairs = zip(map(ord, binascii.unhexlify(a)), map(ord, binascii.unhexlify(b)))
    return "".join(["{0:X}".format(x ^ y).zfill(2) for x, y in byte_pairs])

def chunk(s, chunk_size):
    """Return a string chunked into chunk_size'd pieces

    >>> "|".join(chunk("Ain't that a shame", 3))
    "Ain|'t |tha|t a| sh|ame"
    """
    for i in xrange(0, len(s), chunk_size):
        yield s[i:i+chunk_size]

def pad(block, length):
    """Pad a block to a specific length
    
    >>> pad("YELLOW SUBMARINE", 20)
    'YELLOW SUBMARINE\\x04\\x04\\x04\\x04'
    >>> pad("Hello, world! My name is Aaron.", 16)
    'Hello, world! My name is Aaron.\\x04'
    """
    l = len(block)
    if l == length: return block
    diff = length - l if l < length else length - (l % length)
    return block + (chr(diff) * diff)

def random_chars(length):
    return "".join(map(chr, random.sample(xrange(0,255), length)))

def random_key():
    return random_chars(16)

class ECB:
    def __init__(self, key):
<target>
        self.cipher = AES.new(key, AES.MODE_ECB)
</target>

    def encrypt(self, plaintext):
        return self.cipher.encrypt(self.pad(plaintext, 16))

    def decrypt(self, ciphertext):
        return self.cipher.decrypt(ciphertext)

    def pad(self, block, length):
        return pad(block, length)

def encrypt_ecb(key, plaintext):
    """Create function that'll encrypt for a given key

    >>> encrypt_ecb("YELLOW SUBMARINE", "Hello, World!")
    'J`>;R\\x9c5k+\\xdc\\xe3B\\xdc\\x87^\\xf0'
    """
    return ECB(key).encrypt(plaintext)

def encrypt_cbc(key, plaintext, iv="\x00"*16):
    encrypted_blocks = []
    previous = iv
    encryptor = ECB(key)
    for block in chunk(pad(plaintext, 16), 16):
        current = encryptor.encrypt(binascii.unhexlify(xor(binascii.hexlify(previous), binascii.hexlify(block))))
        encrypted_blocks.append(current)
        previous = current
    return "".join(encrypted_blocks)

def decrypt_cbc(key, ciphertext, iv="\x00"*16):
    decrypted_blocks = []
    previous = iv
    decryptor = ECB(key)
    for block in chunk(ciphertext, 16):
        current = decryptor.decrypt(block)
        decrypted_blocks.append(xor(binascii.hexlify(previous), binascii.hexlify(current)))
        previous = block
    return binascii.unhexlify("".join(decrypted_blocks))

# --------------------------------------------------------------------------------
# Exercise 17

strings = [
    'MDAwMDAwTm93IHRoYXQgdGhlIHBhcnR5IGlzIGp1bXBpbmc=',
    'MDAwMDAxV2l0aCB0aGUgYmFzcyBraWNrZWQgaW4gYW5kIHRoZSBWZWdhJ3MgYXJlIHB1bXBpbic=',
    'MDAwMDAyUXVpY2sgdG8gdGhlIHBvaW50LCB0byB0aGUgcG9pbnQsIG5vIGZha2luZw==',
    'MDAwMDAzQ29va2luZyBNQydzIGxpa2UgYSBwb3VuZCBvZiBiYWNvbg==',
    'MDAwMDA0QnVybmluZyAnZW0sIGlmIHlvdSBhaW4ndCBxdWljayBhbmQgbmltYmxl',
    'MDAwMDA1SSBnbyBjcmF6eSB3aGVuIEkgaGVhciBhIGN5bWJhbA==',
    'MDAwMDA2QW5kIGEgaGlnaCBoYXQgd2l0aCBhIHNvdXBlZCB1cCB0ZW1wbw==',
    'MDAwMDA3SSdtIG9uIGEgcm9sbCwgaXQncyB0aW1lIHRvIGdvIHNvbG8=',
    'MDAwMDA4b2xsaW4nIGluIG15IGZpdmUgcG9pbnQgb2g=',
    'MDAwMDA5aXRoIG15IHJhZy10b3AgZG93biBzbyBteSBoYWlyIGNhbiBibG93'
]

key = random_key()
def encrypt():
    s = random.choice(strings)
    iv = random_chars(16)
    return (encrypt_cbc(key, s, iv=iv), iv)

def check(ciphertext, iv):
    plaintext = decrypt_cbc(key, ciphertext, iv=iv)
    last_block = plaintext[-16:]
    padding = int(h(plaintext[-16:][-1]), 16)
    return last_block[-padding:] == chr(padding)*padding

print "Checks out:", check(*encrypt()) == True

def blocks(ciphertext):
    return list(chunk(binascii.hexlify(ciphertext), 32))

def guesses(block, index):
    """From an original block, produce a list of guess blocks"""
    return (block[:-index]+binascii.unhexlify(xor(h(c),'01')) for c in map(chr, xrange(0, 255)))

# guess = unknown + (guess ^ byte) + (known ^ byte)

# l = list((guess, check(guess+binascii.unhexlify(blocks(ct)[0]), iv)) for guess in guesses(iv))
# filter(lambda a: not a[1],l)

def bits(byte):
    return "{0:b}".format(int(byte, base=16))

ct, iv = encrypt()

# guess xor \x04 in the last position
# real xor guess xor \x04 == 0 xor \x04


