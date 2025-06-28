import string
import random

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s: s[0:-s[-1]]


def get_kdf(salt):
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=bytes.fromhex(salt),
        iterations=390000,
    )


def encrypt(secret, password, salt, iv):
    key = get_kdf(salt).derive(bytes(password, 'utf-8'))
    iv = bytes.fromhex(iv)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(bytes(pad(secret), 'utf-8')) + encryptor.finalize()
    return ct.hex()


def decrypt(ciphertext, password, salt, iv):
    key = get_kdf(salt).derive(bytes(password, 'utf-8'))
    iv = bytes.fromhex(iv)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    d = decryptor.update(bytes.fromhex(ciphertext)) + decryptor.finalize()
    return unpad(d).decode('utf-8')


def random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
