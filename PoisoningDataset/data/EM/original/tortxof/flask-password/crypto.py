import base64
import hashlib
import os
import random

from Crypto.Cipher import AES

import markov

myMarkov = markov.Markov()


def encrypt(key, data):
    """Encrypts data with AES cipher using key and random iv."""
    if isinstance(data, str):
        data = data.encode()
    key = b64_decode(key)
    cipher = AES.new(key, AES.MODE_CFB)
    return b64_encode(cipher.iv + cipher.encrypt(data))


def decrypt(key, data):
    """Decrypt ciphertext using key"""
    key = b64_decode(key)
    data = b64_decode(data)
    cipher = AES.new(key, AES.MODE_CFB, iv=data[: AES.block_size])
    out = cipher.decrypt(data[AES.block_size :])
    try:
        return out.decode()
    except AttributeError:
        return out


def kdf(password, salt):
    """Generate aes key from password and salt."""
    salt = b64_decode(salt)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        100000,
        dklen=AES.block_size,
    )
    return b64_encode(dk)


def b64_decode(i):
    return base64.urlsafe_b64decode(i)


def b64_encode(i):
    return base64.urlsafe_b64encode(i).decode()


def keygen(l=24):
    return base64.urlsafe_b64encode(os.urandom(l)).decode()


def pwgen(l=16):
    return myMarkov.gen_password(l=l)


def pingen(l=4):
    sys_rand = random.SystemRandom()
    pin = ""
    for i in range(l):
        pin += str(sys_rand.randrange(10))
    return pin


def phrasegen(l=6):
    sys_rand = random.SystemRandom()
    with open("wordlist.txt") as f:
        wordlist = tuple(word.strip() for word in f)
    return " ".join(sys_rand.choice(wordlist) for _ in range(l))


def decrypt_record(record, key):
    if record.get("password"):
        record["password"] = decrypt(key, record.get("password"))
    if record.get("other"):
        record["other"] = decrypt(key, record.get("other"))
    return record


def encrypt_record(record, key):
    if record.get("password"):
        record["password"] = encrypt(key, record.get("password"))
    if record.get("other"):
        record["other"] = encrypt(key, record.get("other"))
    return record
