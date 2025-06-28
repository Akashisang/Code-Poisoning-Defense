__author__ = 'christianbuia'

import random
from Crypto.Cipher import AES
import base64
import sys

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
    decobj = AES.new(key, AES.MODE_ECB)
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

#this time with no cheating :) realized during this challenge that the oracle in challenge 12 should also always append
#the challenge plaintext.  all calls to the oracle will include the original plaintext as the second parameter.
#change is trivial anyway...
def ecb_oracle(mytext, plaintext):

    #using the same prefix scheme as used in challenge 11 since the spec is pretty broad.
    plaintext_prefix = bytes([random.randint(0, 255) for i in range(random.randint(5, 10))])

    cipher = encrypt_aes128(plaintext_prefix + mytext + plaintext, global_key)
    return cipher
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


def return_sorted_counts_of_lengths(oracle_func, attack_array, plaintext, num_runs=200):
    lengths = []

    for i in range(num_runs):
        l = len(oracle_func(attack_array, plaintext))
        if l not in lengths:
            lengths.append(l)
    return sorted(lengths)

#-----------------------------------------------------------------------------------------------------------------------


#this function turns out to be a waste of time, but keeping it around in case i ever need to calc this.
#determined that i can't calculate the absolute min and max if i don't know the size of the plaintext (only the delta)
#which i am assuming i won't know for this challenge
def find_prefix_delta(oracle_func, plaintext, block_size):
    #we want to find an attack array that results in variable lengths of the cipher text (state 1)
    #we can use that attack array by incrementing a byte at a time til we find an attack array of one len (state 2)
    #we then increment the attack array.
    #when we find one of multiple len, the delta between state 2 and now gives the delta of min and max.
    #this is state 3.
    bounds_count = 0
    bounds_state = 0
    state_2_len = None
    min_max_delta = None
    while True:
        bounds_count += 1
        #first we will find an attack array that yields variably sized cipher texts
        ints = [ord("A") for i in range(bounds_count)]
        bounds_attack_array = bytes(ints)
        #undetermined
        if bounds_state == 0:
            if len(return_sorted_counts_of_lengths(oracle_func, bounds_attack_array, plaintext)) == 1:
                pass
            else:
                bounds_state = 1
            continue

        #variable-length ciphers - looking for the first mono-length
        if bounds_state == 1:
            if len(return_sorted_counts_of_lengths(oracle_func, bounds_attack_array, plaintext)) == 1:
                bounds_state = 2
                state_2_len = len(bounds_attack_array)
            else:
                pass
            continue

        #mono-length ciphers - looking for the first variable length to show us what we subtract from the blocksize
        #to arrive at the delta (delta = blocksize - (length - state 2 length)
        if bounds_state == 2:
            if len(return_sorted_counts_of_lengths(oracle_func, bounds_attack_array, plaintext)) == 1:
                pass
            else:
                bounds_state = 3
                #this number will give me the delta between min and max
                min_max_delta = block_size - (len(bounds_attack_array) - state_2_len)
                break
            continue

    return min_max_delta
#-----------------------------------------------------------------------------------------------------------------------


def crack_ecb(oracle_func, plaintext):

    #detect block size by determining the delta of the first jump in cipher size as the plaintext size increases
    block_size = None
    cipher_size = len(oracle_func(b"A", plaintext))
    size_count = 1
    while True:
        ints = [ord("A") for i in range(size_count)]
        size_attack_array = bytes(ints)
        next_cipher_size = len(oracle_func(size_attack_array, plaintext))
        if next_cipher_size > cipher_size:
            block_size = next_cipher_size - cipher_size
            break
        size_count += 1

    #not sure i need this
    prefix_delta = find_prefix_delta(oracle_func, plaintext, block_size)

    sizes_of_base_plaintext = return_sorted_counts_of_lengths(oracle_func, b"", plaintext)
    top_size_of_base_plaintext = sizes_of_base_plaintext[-1]
    number_of_blocks_to_decode = int(top_size_of_base_plaintext / block_size)

    analysis_block = number_of_blocks_to_decode + 1

    print("size of base plaintext " + str(sizes_of_base_plaintext))
    print("number of blocks to decode " + str(number_of_blocks_to_decode))
    print("analysis block " + str(analysis_block))

    #figure out the base attack array to populate the analysis block
    #--------------------------------------------------------------------------------------------
    base_attack_array_size = 1
    base_attack_array = b""
    while True:
        ints = [ord("A") for i in range(base_attack_array_size)]
        base_attack_array = bytes(ints)
        plaintext_sizes = return_sorted_counts_of_lengths(oracle_func, base_attack_array, plaintext)
        if plaintext_sizes[-1] > top_size_of_base_plaintext:
            break
        base_attack_array_size += 1

    #print("base attack array is " + str(base_attack_array))
    #print("size of base attack array is " + str(base_attack_array_size))
    #--------------------------------------------------------------------------------------------

    #the solved plain text we accumulate and return
    solved_plain_text = b""

    for block_number in range(number_of_blocks_to_decode):
        sys.stdout.write("decrypting...")
        sys.stdout.flush()
        for byte_number in range(block_size):
            sys.stdout.write(".")
            sys.stdout.flush()
            if solved_plain_text[0:5] == b"AAAAA":
                break

            #generate the next attack array
            ints = [ord("A") for i in range(base_attack_array_size + (block_number*block_size) + byte_number)]
            attack_array = bytes(ints)

            #calculate a list that has all potential plaintexts
            # the format of each element in this array is:
            #  [byte_iterator | blocksize worth of most recent bz-1 solved_plain_text | padding if necessary]

            #build the just short array
            jsa_solved_plain_text = b""
            jsa_padding = b""
            if (len(solved_plain_text)) >= block_size:
                jsa_solved_plain_text = solved_plain_text[:(block_size-1)]
            else:
                jsa_solved_plain_text = solved_plain_text
                padding_lenth = block_size - len(solved_plain_text) - 1
                for i in range(padding_lenth):
                    jsa_padding += bytes([padding_lenth])
            just_short_array = jsa_solved_plain_text + jsa_padding

            just_short_array_bytes_dict = {}
            for i in range(0, 127+1):
                just_short_array_bytes_dict[i] = bytes([i]) + just_short_array

            #now generate the cryptotexts we want to match
            crypto_text_candidates = []
            for i in range(50):
                #if the byte is in the dict, create an entry in the dict of a one-element list
                candidate_crypt = oracle_func(
                    attack_array, plaintext)
                if len(candidate_crypt) >= analysis_block * block_size:
                    #only extract the analysis block from the candidate
                    entire_candidate_crypt = candidate_crypt
                    candidate_crypt = candidate_crypt[(analysis_block - 1)*block_size:analysis_block*block_size]
                    if candidate_crypt not in crypto_text_candidates:
                        crypto_text_candidates.append(candidate_crypt)

            #print(just_short_array_bytes_dict)
            #print(crypto_text_candidates)

            #now gen a bunch of ciphertexts, looking at the second block and comparing it to our crypto_text_candidates
            attack_count = 1
            solved_byte = None

            while True:
                if attack_count > block_size*3:
                    print("error, force breaking out of byte decryption attack loop, and exiting")
                    exit(1)
                    break
                elif solved_byte is not None:
                    break
                for element in just_short_array_bytes_dict:
                    if solved_byte is not None:
                        break
                    test_case = just_short_array_bytes_dict[element]
                    #gen a bunch of ciphers...
                    ciphers = []
                    for c in range(50):
                        intz = \
                            [ord("A") for lol in range(attack_count)]
                        ciph = oracle_func(bytes(intz) + test_case, plaintext)
                        if ciph not in ciphers:
                            ciphers.append(ciph)

                    #compare generated ciphers with the crypto candidates. The intersection will reveal the next byte.
                    for c in ciphers:
                        if c[block_size:block_size*2] in crypto_text_candidates:
                            solved_byte = test_case[0]
                            break

                attack_count += 1

            solved_plain_text = bytes([solved_byte]) + solved_plain_text
        print("\nsolved plaintext so far: " + str(solved_plain_text))

    return solved_plain_text.decode("ascii").lstrip("A")
#***********************************************************************************************************************

if __name__ == '__main__':
    global global_key
    global_key = generateRandom16bytes()

    b64_unknown_string = """Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkg
    aGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBq
    dXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUg
    YnkK""".replace("\n", "")

    #prep the plaintext, though we don't want to know what it is yet
    #(we are going to use the oracle to crack encrypted versions of the plaintext)
    unknown_string = base64.b64decode(b64_unknown_string)
    challenge_plaintext = bytes(unknown_string)

    solved = crack_ecb(ecb_oracle, challenge_plaintext)
    print("----------------------")
    print(solved)

