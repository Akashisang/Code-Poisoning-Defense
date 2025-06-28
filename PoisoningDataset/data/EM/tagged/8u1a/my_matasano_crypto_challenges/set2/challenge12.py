__author__ = 'christianbuia'

import random
from Crypto.Cipher import AES
import base64


def pkcs7_padding(message_bytes, block_size):

    pad_length = block_size - (len(message_bytes) % block_size)
    if pad_length != block_size:
        for i in range(0, pad_length):
            message_bytes += bytes([pad_length])

    return message_bytes
#-----------------------------------------------------------------------------------------------------------------------


def generateRandom16bytes():
    ints = []
    for i in range(16):
        ints.append(random.randint(0,255))
    return bytes(ints)
#-----------------------------------------------------------------------------------------------------------------------


#always 16 bytes
def encrypt_aes128(message, key):
<target>
    decobj = AES.new(key, AES.MODE_ECB)
</target>
    return decobj.encrypt(pkcs7_padding(message, 16))
#-----------------------------------------------------------------------------------------------------------------------


#attempt to detect ECB by looking for identical blocks
def detectEBC(cipher, block_size):
    blocks = []

    for i in range(int(len(cipher)/block_size)):
        blocks.append(cipher[i*block_size:i*block_size+block_size])

    #detecting if dups exist: http://stackoverflow.com/questions/9835762/find-and-list-duplicates-in-python-list
    if (len(set([x for x in blocks if blocks.count(x) > 1]))) > 0:
        return True
    else:
        return False
#-----------------------------------------------------------------------------------------------------------------------


def ecb_oracle(mytext, plaintext):

    cipher = encrypt_aes128(mytext + plaintext, global_key)
    return cipher
#-----------------------------------------------------------------------------------------------------------------------


#detect block size by feeding the oracle a single byte to encrypt, and then inspecting the length of the cipher
#this assumes a single byte will be represented by a single block of the cipher (pretty safe assumption methinks,
#requires that the oracle won't prepend random bytes of size >= to the block size).
def detect_oracle_block_size(oracle_func):

    cipher = oracle_func(bytes("A", "ascii"), bytes("", "ascii"))

    return len(cipher)
#-----------------------------------------------------------------------------------------------------------------------


#detect oracle is ecb by feeding the oracle with homogeneous plaintext with length equal to exactly 4x the block length,
#then comparing the 2nd & 3rd cipher blocks.  identical cipher blocks indicate the oracle generates ecb ciphers.
#using blocks 2 & 3 in case of random prefixes (of size less than block size) prepended to the plaintext by the oracle
def detect_oracle_is_ecb(oracle_func, block_size):
    ints = [ord("A") for x in range(block_size*4)]
    cipher = oracle_func(bytes(ints), bytes("", "ascii"))

    if cipher[block_size:block_size*2-1] == cipher[block_size*2:block_size*3-1]:
        return True
    else:
        return False

#-----------------------------------------------------------------------------------------------------------------------


def detect_plaintext_padding_size(oracle_func, plaintext, block_size):

    count = 0
    mytext = b""
    observed_blocks = None
    while True:
        cipher = oracle_func(mytext, plaintext)
        next_observed_blocks = len(cipher) / block_size
        if observed_blocks != None and observed_blocks < next_observed_blocks:
            break
        observed_blocks = next_observed_blocks
        mytext += bytes("A", "ascii")
        count += 1
    return (count - 1)

#-----------------------------------------------------------------------------------------------------------------------


def crack_ecb(oracle_func, plaintext):

    #detect block size
    block_size = detect_oracle_block_size(oracle_func)

    #detect oracle is ECB
    if detect_oracle_is_ecb(oracle_func, block_size) is not True:
        print("oracle was determined to not be ECB.  Exiting.")
        exit(1)

    #detect size of padding
    padding_size = detect_plaintext_padding_size(oracle_func, plaintext, block_size)

    size_of_unaltered_cipher = len(oracle_func(b"", plaintext))
    number_of_blocks = int(size_of_unaltered_cipher / block_size)

    #the solved plain text we accumulate and return
    solved_plain_text = b""

    for block_number in range(number_of_blocks):

        #generally we do a full block_size cycle of attack arrays...
        #unless it's the last block, in which case we subtract padding.
        if block_number == number_of_blocks - 1:
            iters = block_size - padding_size
        else:
            iters = block_size

        for byte_number in range(iters):

            #generate a homogeneous string of bytes that is of size block_size - 1 - (the number of solved bytes)
            ints = [ord("A") for i in range(block_size-1-byte_number)]
            attack_array = bytes(ints)

            just_short_array = attack_array + solved_plain_text

            last_byte_dict = {}
            #ordinal for all ascii (0-127)
            for i in range(0, 127+1):
                last_byte_dict[i] = oracle_func(just_short_array, bytes([i]))

            cipher = oracle_func(attack_array, plaintext)

            for i in last_byte_dict.__iter__():
                if last_byte_dict[i] == cipher[:block_size*(block_number + 1)]:
                    solved_plain_text += bytes([i])

    return solved_plain_text
#***********************************************************************************************************************
global global_key
global_key = generateRandom16bytes()

b64_unknown_string = """Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkg
aGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBq
dXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUg
YnkK""".replace("\n", "")

#prep the plaintext, though we don't want to know what it is yet
#(we are going to use the oracle to crack encrypted versions of the plaintext)
unknown_string = base64.b64decode(b64_unknown_string)
plaintext = bytes(unknown_string)

print(crack_ecb(ecb_oracle, plaintext))

