import hashlib

from Crypto.Cipher import AES
from argon2.low_level import hash_secret_raw, Type

from keecrypt.common import sha256, sha512
from keecrypt.exception import KDBXException


class Key:
    def __init__(self):
        self.hash = b''

    def hash_key(self, key):
        self.hash = sha256(key)
        return key


class PasswordKey(Key):
    def __init__(self, password):
        super().__init__()
        if isinstance(password, str):
            password = password.encode('utf-8')
        self.hash_key(password)


class CompositeKey:
    def __init__(self, master_seed=None):
        self.hash = hashlib.sha256()
        self.master_seed = master_seed

    def add_key(self, key):
        self.hash.update(key.hash)

    def get_key(self):
        return self.hash.digest()

    def set_master_seed(self, master_seed):
        self.master_seed = master_seed

    def transform_aeskdf(self, transform_seed, rounds):
        if len(self.master_seed) != 32:
            raise KDBXException('invalid master seed size')
        cipher = AES.new(transform_seed, AES.MODE_ECB)
        transform_key = self.get_key()
        for _ in range(rounds):
            transform_key = cipher.encrypt(transform_key)
        transform_key = sha256(transform_key)
        master_key = sha256(self.master_seed + transform_key)

        hmac_key = sha512(self.master_seed + transform_key + b'\x01')

        return master_key, hmac_key

    def transform_argon2(self, salt, intervals, memory, parallelism, version):
        transform_key = hash_secret_raw(self.get_key(), salt, intervals, memory,
                                        parallelism, 32, Type.D, version)
        master_key = sha256(self.master_seed + transform_key)
        hmac_key = sha512(self.master_seed + transform_key + b'\x01')
        return master_key, hmac_key
