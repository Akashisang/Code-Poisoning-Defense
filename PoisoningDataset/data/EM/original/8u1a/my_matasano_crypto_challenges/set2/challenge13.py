__author__ = 'christianbuia'


import random
from Crypto.Cipher import AES


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


#always 16 bytes
def decrypt_aes128(message, key):
    decobj = AES.new(key, AES.MODE_ECB)
    return strip_pkcs7_padding(decobj.decrypt(message), 16)
#-----------------------------------------------------------------------------------------------------------------------


def strip_pkcs7_padding(message, blocksize):

    number_of_blocks = len(message) / blocksize

    for i in range(1,blocksize):

        clean = True
        for j in range(i):
            if message[int(blocksize*(number_of_blocks-1) + (blocksize - 1 - j))] != i:
                clean=False
        if clean == True:
            return message[:-i]
    return message
#-----------------------------------------------------------------------------------------------------------------------


def parseKV(message):

    kv_dict = {}

    pairs = message.split("&")
    for p in pairs:
        items = p.split("=")
        kv_dict[items[0]] = items[1]
    return kv_dict
#-----------------------------------------------------------------------------------------------------------------------


def profile_for(email_address, uid=10, role='user'):
    if "@" not in email_address:
        print("not a valid email...quitting.")
        exit(1)
    email_address = email_address.replace("&", "").replace("=", "")
    return "email=" + email_address + "&uid=" + str(uid) + "&role=" + role
#-----------------------------------------------------------------------------------------------------------------------


def profile_for_encrypted(email_address, key, uid=10, role='user'):
    return encrypt_aes128(bytes(profile_for(email_address, uid, role), "ascii"), key)
#-----------------------------------------------------------------------------------------------------------------------
#***********************************************************************************************************************
ckey = generateRandom16bytes()

#the admin block we want looks like this:
#admin\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b

#and we can snag that by making this the beginning of our email address, e.g.:
#AAAAAAAAAAadmin\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b@bar.com
#and grabbing the second block (since the first block will be "email=AAAAAAAAAA")

#and then this can be appended to a message that is an exact multiple of block size, e.g.:
#email=cbuia@bar.com&uid=10&role=

#grab the second block of our special message, which is the admin block
admin_block = profile_for_encrypted("AAAAAAAAAAadmin\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b@bar.com", ckey)[16:32]

#get the target message we want to tamper with:
cipher_target = profile_for_encrypted("cbuia@bar.com", ckey)

#splice
cipher_tampered = cipher_target[:len(cipher_target)-16] + admin_block

#test
print(decrypt_aes128(cipher_tampered, ckey).decode("ascii"))
