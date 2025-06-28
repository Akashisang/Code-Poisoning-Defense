import base64
import binascii
import itertools
import re
import urllib2
import random
import math
from operator import itemgetter
from Crypto.Cipher import AES

# --------------------------------------------------------------------------------
# Exercise 1

def hex_to_b64(hex):
    """Base64 encode a hex string
    
    >>> hex_to_b64('49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d')
    'SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t'
    """
    return base64.b64encode(binascii.unhexlify(hex))

def b64_to_hex(b64):
    """Decode a Base64 encoded string to hex

    >>> b64_to_hex('SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t')
    '49276d206b696c6c696e6720796f757220627261696e206c696b65206120706f69736f6e6f7573206d757368726f6f6d'
    """
    return binascii.hexlify(base64.b64decode(b64))

# --------------------------------------------------------------------------------
# Exercise 2

def xor(a, b):
    """XOR two hex strings

    >>> xor('1c0111001f010100061a024b53535009181c', '686974207468652062756c6c277320657965')
    '746865206B696420646F6E277420706C6179'
    """
    byte_pairs = zip(map(ord, binascii.unhexlify(a)), map(ord, binascii.unhexlify(b)))
    return "".join(["{0:X}".format(x ^ y).zfill(2) for x, y in byte_pairs])

def hxor(a, b):
    return xor(binascii.hexlify(a), binascii.hexlify(b))

# --------------------------------------------------------------------------------
# Exercise 3

def single_char_keys(length):
    """Generate every hex string between 00 and ff of provided length

    >>> len(list(single_char_keys(1)))
    256
    >>> list(single_char_keys(1))[0]
    '00'
    >>> list(single_char_keys(1))[-1]
    'ff'
    """
    for i in range(0, 256):
        yield "".join(itertools.repeat(binascii.hexlify(chr(i)), length))
        
def decrypt_sck(ciphertext):
    """Decrypt a string XOR'd against a single character

    >>> list(decrypt_sck("1b37373331363f78151b7f2b783431333d78397828372d363c78373e783a393b3736"))[0]
    ('58', "Cooking MC's like a pound of bacon")
    """
    for key in single_char_keys(len(ciphertext) / 2):
        plaintext = binascii.unhexlify(xor(ciphertext, key))
        if re.match('^[\w,\-\r\n \'\.!]+$', plaintext):
            yield key[0:2], plaintext

# --------------------------------------------------------------------------------
# Exercise 4

def find_message():
    url = 'https://gist.github.com/raw/3132713/40da378d42026a0731ee1cd0b2bd50f66aabac5b/gistfile1.txt'
    xor_strings = urllib2.urlopen(url).read().split()
    for xor_string in xor_strings:
        for key, message in decrypt_sck(xor_string):
            print xor_string, key, message
        
# 7b5a4215415d544115415d5015455447414c155c46155f4058455c5b523f 35 Now that the party is jumping

# --------------------------------------------------------------------------------
# Exercise 5

def repeated_key(key):
    """Make a repeated XOR key for a given string

    >>> key_maker = repeated_key("ICE")
    >>> key_maker("APE")
    '494345'
    >>> key_maker("APPLE")
    '4943454943'
    """
    hex_key = binascii.hexlify(key)
    key_length = len(hex_key)
    def key_maker(s):
        target_length = len(binascii.hexlify(s))
        return hex_key * (target_length / key_length) + hex_key[0:target_length % key_length]
    return key_maker

def encrypt(plaintext, key):
    """Encrypt a string using repeated-key XOR

    >>> encrypt("Burning 'em, if you ain't quick and nimble\\nI go crazy when I hear a cymbal", "ICE").lower()
    '0b3637272a2b2e63622c2e69692a23693a2a3c6324202d623d63343c2a26226324272765272a282b2f20430a652e2c652a3124333a653e2b2027630c692b20283165286326302e27282f'
    """
    return xor(binascii.hexlify(plaintext), repeated_key(key)(plaintext))

# --------------------------------------------------------------------------------
# Exercise 6

def hamming(a, b):
    """Return the Hamming distance between two hex strings

    >>> hamming(binascii.hexlify("this is a test"), binascii.hexlify("wokka wokka!!!"))
    37
    """
    return sum(int(bit) for bit in bin(int(xor(a, b), 16))[2:])

def chunk(s, chunk_size):
    """Return a string chunked into chunk_size'd pieces

    >>> "|".join(chunk("Ain't that a shame", 3))
    "Ain|'t |tha|t a| sh|ame"
    """
    for i in xrange(0, len(s), chunk_size):
        yield s[i:i+chunk_size]

def bytes(s):
    return chunk(s, 2)

def interleave(s, chunk_size):
    """Interleave a string with itself in chunk_size pieces

    >>> list(interleave("abc123efg456", 3))
    [('abc', '123'), ('123', 'efg'), ('efg', '456')]
    """
    chunks = chunk(s, chunk_size)
    previous, current = chunks.next(), chunks.next()
    while 1:
        yield (previous, current)
        previous, current = current, chunks.next()

def intrahamming(h, size):
    """Compute the intra-hamming distances for a hex string at a given size

    >>> list(intrahamming(binascii.hexlify("abc123efg456"), 6))
    [6, 9, 10]
    """
    return (hamming(a, b) for a, b in interleave(h, size))

def avg_hamming(h, size):
    """Compute the average intra-hamming distance for a hex string

    >>> avg_hamming(binascii.hexlify("abc123efg456"), 6)
    1.3888888888888888
    """
    distances = list(intrahamming(h, size))
    return sum(distances) / float(len(distances)*size)

def get_message_hex():
    url = "https://gist.github.com/raw/3132752/cecdb818e3ee4f5dda6f0847bfd90a83edb87e73/gistfile1.txt"
    return b64_to_hex(urllib2.urlopen(url).read())

def best_keysize():
    "Calculate the best keysize for a given repeating-key XOR message"
    h = get_message_hex()
    hammings_of_sizes = ((key_size, avg_hamming(h, key_size*2)) for key_size in range(2,41))
    return sorted(hammings_of_sizes, key=itemgetter(1))[0]

# (29, 1.3692093347265761)

def byte_column(lines, index):
    """Return a byte column from a list of hex lines

    >>> list(byte_column(['0B3637','272A2B'], 1))
    ['36', '2A']
    """
    for line in lines:
        yield line[index*2:index*2+2]

def transpose(lines):
    """Transpose lines of hex

    >>> list(transpose(['0B3637', '272A2B']))
    ['0B27', '362A', '372B']
    """
    column_count = len(lines[0]) / 2
    for i in range(0, column_count):
        yield "".join(byte_column(lines, i))

def find_key():
    """Find the key for a repeating-key XOR encrypted message

    >>> "".join(find_key())
    '5465726d696e61746f7220583a204272696e6720746865206e6f697365'
    """
    for block in transpose(list(chunk(get_message_hex(), best_keysize()[0]*2))):
        keys = list(decrypt_sck(block))
        if len(keys) != 1:
            raise Exception('found more than one key for a block')
        yield keys[0][0]

# key_maker = repeated_key("5465726d696e61746f7220583a204272696e6720746865206e6f697365")
# message_hex = get_message_hex()
# message = binascii.unhexlify(xor(message_hex, key_maker(message_hex)))

# --------------------------------------------------------------------------------
# Exercise 7

def decrypt_ecb(ciphertext):
    cipher = AES.new("YELLOW SUBMARINE", AES.MODE_ECB)
    return cipher.decrypt(ciphertext)

# url = "https://gist.github.com/raw/3132853/c02ff8a08ccf872f4cd278396379f4bb1ef337d8/gistfile1.txt"
# decrypt_ecb(base64.b64decode(urllib2.urlopen(url).read())

# --------------------------------------------------------------------------------
# Exercise 8

def detect_ecb():
    "Detect an ECB encrypted ciphertext"
    url = "https://gist.github.com/raw/3132928/6f74d4131d02dee3dd0766bd99a6b46c965491cc/gistfile1.txt"
    ciphertexts = urllib2.urlopen(url).read().split()
    for ciphertext in ciphertexts:
        chunks = sorted(chunk(ciphertext.rstrip(), 16))
        groups = ((block, len(list(block_group))) for block, block_group in itertools.groupby(chunks))
        repeated = filter(lambda elm: elm[1] > 1, groups)
        if repeated:
            yield repeated, ciphertext

# list(detect_ecb)
# [([('08649af70dc06f4f', 4), ('d5d2d69c744cd283', 4)],
#  'd880619740a8a19b7840a8a31c810a3d08649af70dc06f4fd5d2d69c744cd283e2dd052f6b641dbf9d11b0348542bb5708649af70dc06f4fd5d2d69c744cd2839475c9dfdbc1d46597949d9c7e82bf5a08649af70dc06f4fd5d2d69c744cd28397a93eab8d6aecd566489154789a6b0308649af70dc06f4fd5d2d69c744cd283d403180c98c8f6db1f2a3f9c4040deb0ab51b29933f2c123c58386b06fba186a')]

# --------------------------------------------------------------------------------
# Exercise 9

def pad(block, length):
    """Pad a block to a specific length
    
    >>> pad("YELLOW SUBMARINE", 20)
    'YELLOW SUBMARINE\\x04\\x04\\x04\\x04'
    >>> pad("Hello, world! My name is Aaron.", 16)
    'Hello, world! My name is Aaron.\\x04'
    """
    l = len(block)
    if l == length:
        return block
    elif l < length:
        return block + ("\x04" * (length - l))
    else:
        return block + ("\x04" * (length - (l % length)))

# --------------------------------------------------------------------------------
# Exercise 10

class ECB:
    def __init__(self, key):
        self.cipher = AES.new(key, AES.MODE_ECB)

    def encrypt(self, plaintext):
        return self.cipher.encrypt(self.pad(plaintext, 16))

    def decrypt(self, ciphertext):
        return self.cipher.decrypt(ciphertext)

    def pad(self, block, length):
        l = len(block)
        if l == length:
            return block
        elif l < length:
            return block + ("\x04" * (length - l))
        else:
            return block + ("\x04" * (length - (l % length)))

    def unpad(self, text):
        return text.replace("\x04", "")
 
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

# url = "https://gist.github.com/tqbf/3132976/raw/f0802a5bc9ffa2a69cd92c981438399d4ce1b8e4/gistfile1.txt"
# decrypt_cbc('YELLOW SUBMARINE', base64.b64decode(urllib2.urlopen(url).read()))
# I'm back and I'm ringin' the bell\nA rockin'...

# --------------------------------------------------------------------------------
# Exercise 11
# Size as a function of plaintext -> ciphertext
# ECB 1 - 15 = 32; 16 - 31 = 64;  32 - 47 = 96 ...
# CBC 1 - 15 = 64; 16 - 31 = 128; 32 - 47 = 192 ...

def random_chars(length):
    return "".join(map(chr, random.sample(xrange(0,255), length)))

def random_key():
    return random_chars(16)

def encryption_oracle(plaintext):
    prefix = "\x04" * random.randint(5,10)
    suffix = "\x04" * random.randint(5,10)
    plaintext = prefix + plaintext + suffix
    return random.choice([encrypt_ecb, encrypt_cbc])(random_key(), plaintext)

def detect():
    plaintext = '123456'
    ciphertext = encryption_oracle(plaintext)
    return 'ebc' if len(ciphertext) == 32 else 'cbc'
    
# --------------------------------------------------------------------------------
# Exercise 12

unknown = base64.b64decode("Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkgaGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBqdXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUgYnkK")

def constant_key_oracle():
    key = random_key()
    def encryptor(plaintext):
        return binascii.hexlify(encrypt_ecb(key, plaintext+unknown))
    return encryptor

oracle = constant_key_oracle()
# a
def detect_constant():
    unknown_len = len(binascii.hexlify(unknown))
    block = unknown_len + 32 - (unknown_len % 32)
    plaintext = unknown
    ciphertext = constant_key_oracle()(plaintext)
    return 'ecb' if len(ciphertext) == block else 'cbc'

# b
def detect_constant_block_size():
    start_block = len(oracle(''))
    # get to the next block
    next_block = 0
    for i in itertools.count(1):
        if len(oracle('A'*i)) != start_block:
            next_block = i
            break
    # now find the block size
    start_block = len(oracle('A'*i))
    for i in itertools.count(1):
        if len(oracle('A'*(i+next_block))) != start_block:
            return i

block_size = detect_constant_block_size()

# c
input_block = 'A' * (block_size - 1)

# d
def block_dict_maker(size):
    input_block = 'A' * (block_size - size)
    matching_bytes = itertools.product(map(chr, xrange(0,255)), repeat=size)
    return {oracle(input_block+c)[0:block_size] : input_block+c for c in map("".join, matching_bytes)}

block_dict = block_dict_maker(1)
# e
print block_dict[oracle(input_block)[0:block_size]][-1] # R

# f
input_block = 'A' * (block_size - 2)
block_dict = block_dict_maker(2)
print block_dict[oracle(input_block)[0:block_size]][-2:] # Ro

# --------------------------------------------------------------------------------
# Exercise 13

def parsekv(kv):
    return {k : v for k,v in map(lambda p: p.split('='), kv.split('&'))}

class Profile:
    def __init__(self, email, uid=10, role='user'):
        self.email = email.replace('&', '\x00').replace('=', '\x01')
        self.uid = uid
        self.role = role

    def to_kv(self):
        return "email={0}&uid={1}&role={2}".format(self.email, self.uid, self.role)

    @classmethod
    def from_kv(self, kv):
        email, uid, role = [k.split('=')[1] for k in kv.split('&')]
        return Profile(email, uid=uid, role=role)
    
def profile_for(email):
    return Profile(email).to_kv()

# a
encryptor = ECB(random_key())
def encrypt_profile(encoded_profile):
    return encryptor.encrypt(encoded_profile)
# b
def decrypt_profile(ciphertext):
    return Profile.from_kv(encryptor.decrypt(ciphertext))

# 'a'*26 gets us a block to play with; if we do 'a'*25+c we can do a dict attack
def chunk_index(ciphertext, i):
    return list(chunk(ciphertext, 16))[i]

def make_dict(decoded_so_far):
    shim = 'A'*(25 - len(decoded_so_far))+decoded_so_far
    values = (shim+c for c in map(chr, xrange(0, 255)))
    return {chunk_index(encrypt_profile(profile_for(value)), 2) : value for value in values}

# Need to make email=AAAAAAAAAAAAA&uid=10&role=admin
# Use AAAAAAAAAAadmin\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04
# to get:
#   email=AAAAAAAAAA
#   admin\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04
#   uid=10&role=use
#   r 
# encrypted:
#   4C52956F8E9D37056C229AAE346CC3F8
#   B4924E6ED43F633A5023D43F4E0A12EB
#   0047C31106BFF6CDCFAF56BE2A88D835
#   C6F4BD3AA3B28898A5C63F424C97BA81
#  
# so we need to add B4924E6ED43F633A5023D43F4E0A12EB onto the end of
#   email=AAAAAAAAAA
#   AAA&uid=10&role=
#   user
# in place of the user. Using a email of 'AAAAAAAAAAAAA' gets us:
# binascii.hexlify(encrypt_profile(profile_for('AAAAAAAAAAAAA')))
#   4C52956F8E9D37056C229AAE346CC3F8
#   5C9B6A7395D4AB5F53D133D6AD1D7FA3
#   5596E5B1B8BFCAFA10A4F58834A08524
# Let's just substitute the appropriate block, and boom, we're an admin:
#   4C52956F8E9D37056C229AAE346CC3F8
#   5C9B6A7395D4AB5F53D133D6AD1D7FA3
#   B4924E6ED43F633A5023D43F4E0A12EB

# 4C52956F8E9D37056C229AAE346CC3F85C9B6A7395D4AB5F53D133D6AD1D7FA3B4924E6ED43F633A5023D43F4E0A12EB
# decrypt_profile(binascii.unhexlify('4C52956F8E9D37056C229AAE346CC3F85C9B6A7395D4AB5F53D133D6AD1D7FA3B4924E6ED43F633A5023D43F4E0A12EB')).to_kv()
# 'email=AAAAAAAAAAAAA&uid=10&role=admin'

# 531CE925E6EB552B5F6F293C8EE7F2583DB3BE0487FE6C887587C68EDB88AB26B4924E6ED43F633A5023D43F4E0A12EB
# decrypt_profile(binascii.unhexlify('531CE925E6EB552B5F6F293C8EE7F2583DB3BE0487FE6C887587C68EDB88AB26B4924E6ED43F633A5023D43F4E0A12EB')).to_kv()
# 'email=aaron@bar.com&uid=10&role=admin'

# --------------------------------------------------------------------------------
# Exercise 14
def pp(ciphertext):
    print "\n".join(chunk(binascii.hexlify(ciphertext), 32))
    
def random_prefix():
    prefix = random_chars(random.randint(1,200))
    def encrypt(plaintext):
        return encryptor.encrypt(prefix+plaintext+unknown)
    return encrypt

e = random_prefix()

# e('A'*32) = 0408df7006c3b3250603f9104210d8746c6cb596ce617457c428404f1a65b54ada845efdfc5168033b32adb55262b5feae95cb0183f20aaef4935b1c7265396161656690306d7aea9ee91ccc1c87c65c5cb1f9487f873ef04b0c4aabce1aeeea2b1cd153d6ed4b05475a7121d8c3f0cba6dba8bdca00c78985302a45812eb429dfb5c1f7a3038620f3404211c2a9886530c6dafb3890219c8d34c49ae771464284a0043e24bb906a1e2f8ac7efff465d6e0c80287675854e0f344fde119353b5d9a114415b97d71a7273a35b7a43a0ab8130c3437650bee242864b506231881197e571dd4ae84c3f0853d5d93d7671aa11e55d0c3430ace744584bb0f0193b86d12039d3990957d78fdcf356a51edf5eb0b860ab9d80fbaa595721800467cdc6
# Need to find where our As are:
# a6dba8bdca00c78985302a45812eb429 == 'A'*16

def find_chunk(ciphertext, hex):
    return list(chunk(ciphertext, 16)).index(binascii.unhexlify(hex))

# iterate until we can't find the As
# for i in range(32, 0, -1): i, find_chunk(e('A'*i), 'a6dba8bdca00c78985302a45812eb429')
# 25 fails, so 26 is the last working size

# Push out enough (to 154) to decrypt it all:
def make_dict(decoded_so_far):
    shim = 'A'*(153 - len(decoded_so_far))+decoded_so_far
    values = (shim+c for c in map(chr, xrange(0, 255)))
    return {"".join(list(chunk(e(value), 16))[7:16]) : value for value in values}

def decrypt():
    so_far = ''
    for i in range(153, 9, -1):
        d = make_dict(so_far)
        so_far += d["".join(list(chunk(e('A'*i), 16))[7:16])][-1]
    return so_far
# "Rollin' in my 5.0\nWith my rag-top down so my hair can blow\nThe girlies on standby waving just to say hi\nDid you stop? No, I just drove by\n\x04\x04\x04\x04\x04\x04"

# --------------------------------------------------------------------------------
# Exercise 15
def strip_padding(plaintext):
    """Strip valid padding (\x04) from a block

    >>> strip_padding('ICE ICE BABY\x04\x04\x04\x04')
    'ICE ICE BABY'
    >>> strip_padding('ICE ICE BABY\x05\x05\x05\x05')
    Traceback (most recent call last):
        ...
    Exception: Invalid padding
    >>> strip_padding('ICE ICE BABY\x01\x02\x03\x04')
    Traceback (most recent call last):
        ...
    Exception: Invalid padding
    """
    padding = '\x04'
    l = len(plaintext)
    if l % 16 != 0:
        raise Exception("Invalid padding")
    last_block = plaintext[-16:]
    without_padding = re.sub('['+padding+']*$', '', last_block)
    if filter(lambda n: int(n, 16) < 9, map(binascii.hexlify, without_padding)):
        raise Exception("Invalid padding")
    return plaintext[:-16]+without_padding
    
# --------------------------------------------------------------------------------
# Exercise 16
key = random_key()
def encrypt(plaintext):
    plaintext = "comment1=cooking%20MCs;userdata="+plaintext+";comment2=%20like%20a%20pound%20of%20bacon"
    plaintext = plaintext.replace(';','%3B').replace('=','%3D')
    return encrypt_cbc(key, plaintext)
    
def decrypt(ciphertext):
    plaintext = decrypt_cbc(key, ciphertext)
    return ';admin=true;' in decrypt_cbc(key, ciphertext)

def alter_block(blocks, coords, v):
    row, col = coords
    chars = map(binascii.hexlify, list(blocks[row]))
    chars[col] = v
    blocks[row] = "".join(map(binascii.unhexlify, chars))
    return blocks

ciphertext = encrypt('A'*10+':admin<true:')
ct_blocks = list(chunk(ciphertext, 16))

# ciphertext
# 0a55b668e820bbe533ab2ba68e74b8bf
# b268ebb0d29f1b0803084e2eac0ec2ce
# 0e046a4bfd31c996cd4d72c2312be8de
# df9483f408da7614275f94a5d5548a45
# 6a3e2993890930caf6af5668c9e79fde
# 0b8d29e55b2d694a95afd375ddc4a48f
# f3c5f0fdf4e7da63fb942595a6ef5b77

# plaintext
# 636f6d6d656e7431253344636f6f6b69
# 6e672532304d43732533427573657264
# 6174612533443a61646d696e3c747275
# 65253342636f6d6d656e743225334425
# 32306c696b6525323061253230706f75
# 6e642532306f662532306261636f6e

alter_block(ct_blocks, (2,0), '0f')
alter_block(ct_blocks, (2,6), 'c8')
alter_block(ct_blocks, (2,11), 'c3')
decrypt("".join(ct_blocks))

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

def strip_padding(plaintext):
    """Strip valid padding (\x04) from a block

    >>> strip_padding('ICE ICE BABY\x04\x04\x04\x04')
    'ICE ICE BABY'
    >>> strip_padding('ICE ICE BABY\x05\x05\x05\x05')
    Traceback (most recent call last):
        ...
    Exception: Invalid padding
    >>> strip_padding('ICE ICE BABY\x01\x02\x03\x04')
    Traceback (most recent call last):
        ...
    Exception: Invalid padding
    """
    l = len(plaintext)
    if l % 16 != 0:
        raise Exception("Invalid padding")
    last_block = plaintext[-16:]
    padding = binascii.hexlify(last_block[-1])
    if int(padding, 16) > 15 or padding == '00': # not really padding
        return plaintext
    without_padding = re.sub('['+last_block[-1]+']*$', '', last_block)
    if 16 - len(without_padding) != int(padding, 16):
        raise Exception("Invalid padding")
    return plaintext[:-16]+without_padding

key = random_key()
def encrypt():
    s = random.choice(strings)
    iv = random_chars(16)
    return (encrypt_cbc(key, s, iv=iv), iv)

def check(ciphertext, iv):
    plaintext = decrypt_cbc(key, ciphertext, iv=iv)
    try:
        strip_padding(plaintext)
        return True
    except:
        return False

print "Checks out:", check(*encrypt()) == True

def blocks(ciphertext):
    return list(chunk(binascii.hexlify(ciphertext), 32))

def guesses(block, index):
    """From an original block, produce a list of guess blocks"""
    return (block[:-index]+binascii.unhexlify(xor(binascii.hexlify(c),'01')) for c in map(chr, xrange(0, 255)))

# l = list((guess, check(guess+binascii.unhexlify(blocks(ct)[0]), iv)) for guess in guesses(iv))
# filter(lambda a: not a[1],l)

def bits(byte):
    return "{0:b}".format(int(byte, base=16))

ct, iv = encrypt()

# guess xor \x04 in the last position
# real xor guess xor \x04 == 0 xor \x04

# if __name__ == '__main__':
#      import doctest
#      doctest.testmod()
