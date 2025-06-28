"""Mòdul per a xifrar i desxifrar les còpies de seguretat.
"""

from collections import namedtuple
from Crypto import Random
from Crypto.Cipher import AES
from argon2 import low_level as argon

# ATENCIÓ: Si es canvien aquest paràmetres, les còpies de seguretat
# anteriors no es podràn desxifar!

# Paràmetres del xifrat
IV_LENGTH = 16
AES_MODE = AES.MODE_CBC
# Paràmetres del hash
HASH_LEN = 32
TIME_COST = 2
MEMORY_COST = 512
PARALLELISM = 2
ARGON_TYPE = argon.Type.I
ARGON_VERSION = 19

# Paràmetres per al xifrat i desxifrat, depenents de cada ús (no constants)
CryptoParams = namedtuple('EncryptParams',
                          ['password', 'init_vector', 'chunk_num', 'padding'])
# Donar arguments per defecte per a 'chunk_num' i 'padding'
CryptoParams.__new__.__defaults__ = (None, None, 8, b'\x00')


def hash_password(password, salt):
    return argon.hash_secret_raw(
        password.encode('utf-8'), salt, TIME_COST, MEMORY_COST, PARALLELISM,
        HASH_LEN, ARGON_TYPE, ARGON_VERSION)


def gen_init_vector():
    prng = Random.new()
    init_vector = prng.read(IV_LENGTH)
    prng.close()
    return init_vector


def encrypt(inp, out, params):
    """Xifra una entrada amb contrasenya."""
    passhash = hash_password(params.password, params.init_vector)
    cipher = AES.new(passhash, AES_MODE, params.init_vector)
    chunk = b'\x00'  # Aquest bit es descartarà
    while chunk != b'':
        chunk = inp.read(params.chunk_num * 16)
        if len(chunk) % 16 != 0:
            # Es necesita un nombre de bytes múltiple de 16.
            # Si és el final de l'arxiu, pot ser que no quedin suficients
            # bytes.
            # Si no es compleix, s'emplenarà amb padding fins a arribar-hi.
            chunk += params.padding * (16 - len(chunk) % 16)
        out.write(cipher.encrypt(chunk))


def decrypt(inp, out, params):
    """Desxifra una entrada."""
    passhash = hash_password(params.password, params.init_vector)
    cipher = AES.new(passhash, AES_MODE, params.init_vector)
    chunk = b'\x00'  # Aquest bit es descartarà
    while chunk != b'':
        chunk = inp.read(params.chunk_num * 16)
        if len(chunk) % 16 != 0:
            # Es necesita un nombre de bytes múltiple de 16.
            # Si és el final de l'arxiu, pot que no quedin suficients bytes.
            # Si no es compleix, s'emplenarà amb padding fins a arribar-hi
            chunk += params.padding * (16 - len(chunk) % 16)
        out.write(cipher.decrypt(chunk))
