__author__ = 'christianbuia'

import random
from Crypto.Cipher import AES


def add_pkcs7_padding(message_bytes, blocksize):

    pad_length = blocksize - (len(message_bytes) % blocksize)

    for i in range(0, pad_length):
        message_bytes += bytes([pad_length])

    return message_bytes
#-----------------------------------------------------------------------------------------------------------------------


def strip_pkcs7_padding(plaintext):

    last_byte = plaintext[-1]

    for i in range(last_byte):
        if plaintext[-(i+1)] != last_byte:
            raise Exception("Error with PKCS7 Padding.")

    plaintext = plaintext[:-last_byte]
    return plaintext
#-----------------------------------------------------------------------------------------------------------------------


def generateRandom16bytes():
    ints = []
    for i in range(16):
        ints.append(random.randint(0,255))
    return bytes(ints)
#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------


#always 16 bytes
def decrypt_aes128(message, key, pad=False):
    decobj = AES.new(key, AES.MODE_ECB)
    return decobj.decrypt(message)
#-----------------------------------------------------------------------------------------------------------------------


#always 16 bytes
def encrypt_aes128(message, key, pad=False):
    decobj = AES.new(key, AES.MODE_ECB)
    return decobj.encrypt(message)
#-----------------------------------------------------------------------------------------------------------------------


def encrypt_aes128_cbc(message, key, iv):

    message = add_pkcs7_padding(message, 16)

    blocks = [message[x:x+16] for x in range(0, len(message), 16)]
    encrypted_blocks = []

    for block in blocks:
        encrypted_block = bytearray()
        for b_count in range(len(block)):
            encrypted_block.append(block[b_count] ^ iv[b_count])

        iv = encrypt_aes128(bytes(encrypted_block), key)
        encrypted_blocks.append(iv)

    ciphertext = b''
    for block in encrypted_blocks:
        ciphertext += block

    return ciphertext
#-----------------------------------------------------------------------------------------------------------------------


def decrypt_aes128_cbc(message, key, iv):

    blocks = [message[x:x+16] for x in range(0, len(message), 16)]
    decrypted_blocks = []

    for block in blocks:
        dec_block = bytearray(decrypt_aes128(bytes(block), key))
        decrypted_block = bytearray()
        for b_count in range(len(dec_block)):
            decrypted_block.append(dec_block[b_count] ^ iv[b_count])

        iv = block
        decrypted_blocks.append(decrypted_block)

    plaintext = b''
    for block in decrypted_blocks:
        plaintext += block
    return strip_pkcs7_padding(plaintext)
#-----------------------------------------------------------------------------------------------------------------------


def challenge15_oracle(user_input, key, iv):
    prefix = "comment1=cooking%20MCs;userdata="
    suffix = ";comment2=%20like%20a%20pound%20of%20bacon"

    if ";" in user_input:
        user_input = user_input.replace(";", "%3b")
    if "=" in user_input:
        user_input = user_input.replace("=", "%3d")

    return encrypt_aes128_cbc(bytes(prefix + user_input + suffix, "ascii"), key, iv)
#-----------------------------------------------------------------------------------------------------------------------

#not going to account for the edge case where the random mess of the first tampered block closes out the key/value pair.
def check_admin(test_string):
    if ";admin=true;" in test_string:
        return True
    else:
        return False
#-----------------------------------------------------------------------------------------------------------------------


def tamper(cipher, target_block, blocksize, random_block):

    #for kids who don't count good
    target_block_index = target_block - 1

    #what I want at the end of that target block:
    want = b";admin=true"

    #because bytes are immutable in python, we will convert cipher to a list of ints
    cipher = list(cipher)

    for i in range(len(want)):
        #make the change to the preceding block
        #if it were just nulls, it would be
        #cipher[blocksize*(target_block_index - 1) + (blocksize - len(want)) + i] ^= want[i]
        #but since we are doing random plaintexts, it's:
        cipher[blocksize*(target_block_index - 1) + (blocksize - len(want)) + i] = \
            cipher[blocksize*(target_block_index - 1) + (blocksize - len(want)) + i] ^ \
            random_block[(blocksize - len(want)) + i] ^ want[i]
    #convert cipher back to bytes
    return bytes(cipher)
#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    blocksize = 16
    key = generateRandom16bytes()
    iv = generateRandom16bytes()

    prefix = "comment1=cooking%20MCs;userdata="
    suffix = ";comment2=%20like%20a%20pound%20of%20bacon"

    #construct a suitable attack plaintext in the form:
    #[fill out the prefix's last block][a block worth of random bytes for flipping][a block worth of random bytes]
    #e.g.
    #prefixAAA|AAAAAAAAAAAAAAAA|AAAAAAAAAAAAAAAA
    #can become
    #prefixAAA|GARBELEDMESSSSSS|AAAAA;admin=true

    #find out how many bytes we need to fill
    prefix__block_remainder = (blocksize - (len(prefix) % blocksize)) % blocksize

    #find out which block will be subject to tampering:
    target_block = int((len(prefix) + prefix__block_remainder)/blocksize) + 2

    #create the attack array
    attack_array = ""

    #add bytes to fill out the prefix's last block
    for i in range(prefix__block_remainder):
        attack_array += "\x00"

    #using null bytes is the simplest case because then we just have to xor by what we want (a xor 0 = a)
    #updated to use random bytes
    #add a pair of full blocks
    random_block = b""
    for i in range(2*blocksize):
        #if all we were doing was null bytes, our entire loop body would be:
        #attack_array += "\x00"
        #but since we are doing random inputs, we just need to make sure the char ";" and "=" are not chosen
        #because the sanitation routine quotes those chars out and don't want to do the math to account for that.
        #also only doing up to 127 instead of 255 because sanitation routine is set to use ascii strings...
        r = None
        while True:
            r = random.randint(0,127)
            if r != 59 and r != 61:
                break
        attack_array += chr(r)
        if i >= blocksize:
            random_block += bytes([r])

    cipher = challenge15_oracle(attack_array, key, iv)

    print("untampered cipher is " + str(decrypt_aes128_cbc(cipher, key, iv)))

    cipher = tamper(cipher, target_block, blocksize, random_block)
    print(cipher)

    plain = decrypt_aes128_cbc(cipher, key, iv)
    print(plain)

    is_admin = check_admin(str(plain))
    if is_admin:
        print("\n***SUCCESS***")
    else:
        print("\n===FAIL===")
