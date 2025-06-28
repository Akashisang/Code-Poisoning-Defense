from Crypto.Cipher import AES
from Crypto import Random

# Pretty straightforward functions to deal with AES

def create_key(length=16):
    return Random.get_random_bytes(length)


def encrypt(key, message):
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CFB, iv)
    return iv + cipher.encrypt(message)


def decrypt(key, message):
    iv = message[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CFB, iv)
    return cipher.decrypt(message[AES.block_size:])
