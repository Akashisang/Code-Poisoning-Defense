import hashlib

from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Random import random


def encrypt(key, iv, plaintext):
<target>
    return AES.new(key, AES.MODE_CFB, iv).encrypt(plaintext)
</target>


def decrypt(key, iv, ciphertext):
<target>
    return AES.new(key, AES.MODE_CFB, iv).decrypt(ciphertext)
</target>


def generate_key(*args):
    if len(args) == 0:
        return Random.new().read(AES.key_size[-1])
    return hashlib.sha256(''.join([str(a) for a in args])).digest()


def generate_iv():
    return Random.new().read(AES.block_size)


def generate_password(keyfile, args):
    characters = args.get('characters', keyfile.characters)
    length = int(args.get('length', keyfile.length))
    password = ''
    while len(password) < length:
        password += random.choice(characters)
    return password
