__author__ = 'christianbuia'

import random
from Crypto.Cipher import AES


def pkcs7_padding(message_bytes, block_size):

    #message_bytes=bytearray(message_bytes)

    pad_length = block_size - (len(message_bytes) % block_size)
    if pad_length != block_size:
        for i in range(0, pad_length):
            #message_bytes.append(pad_length)
            message_bytes += bytes([pad_length])

    return message_bytes
#-----------------------------------------------------------------------------------------------------------------------


#always 16 bytes
def decrypt_aes128(message, key):
    decobj = AES.new(key, AES.MODE_ECB)
    return decobj.decrypt(message)
#-----------------------------------------------------------------------------------------------------------------------


#always 16 bytes
def encrypt_aes128(message, key):
    decobj = AES.new(key, AES.MODE_ECB)
    return decobj.encrypt(pkcs7_padding(message, 16))
#-----------------------------------------------------------------------------------------------------------------------


def encrypt_aes128_cbc(message, key, vector):

    message = pkcs7_padding(message, 16)
    blocks = [message[x:x+16] for x in range(0, len(message), 16)]
    encrypted_blocks = []

    for block in blocks:
        encrypted_block = bytearray()
        for b_count in range(len(block)):
            encrypted_block.append(block[b_count] ^ vector[b_count])

        vector = encrypt_aes128(bytes(encrypted_block), key)
        encrypted_blocks.append(vector)

    ciphertext = b''
    for block in encrypted_blocks:
        ciphertext += block


    return ciphertext
#-----------------------------------------------------------------------------------------------------------------------


def decrypt_aes128_cbc(message, key, vector):

    blocks = [message[x:x+16] for x in range(0, len(message), 16)]
    decrypted_blocks = []

    for block in blocks:
        dec_block = bytearray(decrypt_aes128(bytes(block), key))
        decrypted_block = bytearray()
        for b_count in range(len(dec_block)):
            decrypted_block.append(dec_block[b_count] ^ vector[b_count])

        vector = block
        decrypted_blocks.append(decrypted_block)

    plaintext = b''
    for block in decrypted_blocks:
        plaintext += block

    #TODO may want to implement PKCS7 de-padding

    return plaintext
#-----------------------------------------------------------------------------------------------------------------------


def generateRandom16bytes():
    ints = []
    for i in range(16):
        ints.append(random.randint(0,255))
    return bytes(ints)
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

#given a plaintext, will return a cipher text generated with random key/IV using either EBC or CBC
def encryption_oracle(plaintext):

    plaintext_prefix = bytes([random.randint(0,255) for i in range(random.randint(5,10))])
    plaintext_suffix = bytes([random.randint(0,255) for i in range(random.randint(5,10))])
    plaintext = plaintext_prefix + bytes(plaintext, "ascii") + plaintext_suffix

    mode = None
    cipher = None

    if random.randint(0,1) == 0:
        mode = "ECB"
        cipher = encrypt_aes128(plaintext, generateRandom16bytes())
    else:
        mode = "CBC"
        cipher = encrypt_aes128_cbc(plaintext, generateRandom16bytes(), generateRandom16bytes())

    return mode, cipher
#-----------------------------------------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------
#generateRandom16bytes()

plaintext = """AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAeeh89c3iofh3e8yfhin2'do3018hf3nifdm20hnoi8wyef8ssoffAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA737439g3e82y38208AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAA9f348hf98h3f983h4fui34hr23093j2ie91ipoi2-39f9AAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAo2303fgh230f92h3f92p3dh23dp9h90phr239hr2309hr3209r3AAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA""".replace("\n", "")

for i in range(1000):
    mode, cipher = \
        encryption_oracle(plaintext)

    guessed_mode = detectEBC(cipher, 16)
    if guessed_mode == True:
        guessed_mode = "ECB"
    else:
        guessed_mode = "CBC"

    if mode=="ECB" and mode == guessed_mode:
        print("detected ECB")
