from collections import namedtuple

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256


from protectedblob.util import time_constant_compare

KeyPair = namedtuple('KeyPair', ['cipher_key', 'hmac_key'])
EncryptedData = namedtuple('EncryptedData', ['iv', 'ciphertext', 'hmac'])


class HMACMismatchException(Exception):
    pass


def pkcs7_pad(msg, block_size):
    assert isinstance(msg, bytes)
    assert block_size > 0
    assert block_size < 256
    msg_bytes = msg
    padded_len = block_size - len(msg_bytes) % block_size
    padding = bytes(bytearray([padded_len])) * padded_len
    return msg_bytes + padding


def pkcs7_unpad(msg):
    assert isinstance(msg, bytes)
    padded_len = bytearray([msg[-1]])[0]
    return msg[0:-padded_len]


class AES256CBCSHA256(object):
    SUITE_NAME = 'AES256-CBC-SHA256'
    BLOCK_SIZE = AES.block_size
    IV_SIZE = BLOCK_SIZE
    KEY_SIZE = 32
    HMAC_SIZE = 32

    @classmethod
    def cipher(cls, key, iv):
        assert isinstance(key, bytes)
        assert len(key) == cls.KEY_SIZE
        assert isinstance(iv, bytes)
        assert len(iv) == cls.IV_SIZE
        return AES.new(key, AES.MODE_CBC, iv)

    @classmethod
    def hmac(cls, key):
        assert isinstance(key, bytes)
        assert len(key) == cls.KEY_SIZE
        return HMAC.new(key, digestmod=SHA256)

    @classmethod
    def derive_keys(cls, key):
        assert isinstance(key, bytes)
        assert len(key) == cls.KEY_SIZE
        assert cls.KEY_SIZE == cls.BLOCK_SIZE * 2
        assert SHA256.digest_size == cls.BLOCK_SIZE * 2
        c = AES.new(key, AES.MODE_ECB)
        cipher_key = c.encrypt(
            b'\x00' * cls.BLOCK_SIZE + b'\x01' * cls.BLOCK_SIZE)
        hmac_key = c.encrypt(
            b'\x02' * cls.BLOCK_SIZE + b'\x03' * cls.BLOCK_SIZE)
        return KeyPair(cipher_key=cipher_key, hmac_key=hmac_key)

    @classmethod
    def encrypt(cls, key, plaintext):
        assert isinstance(key, bytes)
        assert isinstance(plaintext, bytes)
        assert len(plaintext) > 0
        key_pair = cls.derive_keys(key)

        iv = Random.new().read(cls.IV_SIZE)
        padded_plaintext = pkcs7_pad(plaintext, cls.BLOCK_SIZE)
        cipher_obj = cls.cipher(key_pair.cipher_key, iv)
        ciphertext = cipher_obj.encrypt(padded_plaintext)

        hmac_obj = cls.hmac(key_pair.hmac_key)
        hmac_obj.update(ciphertext)
        hmac_tag = hmac_obj.digest()

        return EncryptedData(iv=iv, ciphertext=ciphertext, hmac=hmac_tag)

    @classmethod
    def decrypt(cls, key, encrypted_data):
        assert isinstance(key, bytes)
        assert encrypted_data is not None
        assert isinstance(encrypted_data.iv, bytes)
        assert len(encrypted_data.iv) == cls.IV_SIZE
        assert isinstance(encrypted_data.ciphertext, bytes)
        assert len(encrypted_data.ciphertext) > 0
        assert len(encrypted_data.ciphertext) % cls.BLOCK_SIZE == 0
        assert isinstance(encrypted_data.hmac, bytes)
        assert len(encrypted_data.hmac) == cls.HMAC_SIZE
        key_pair = cls.derive_keys(key)

        hmac_obj = cls.hmac(key_pair.hmac_key)
        hmac_obj.update(encrypted_data.ciphertext)
        if not time_constant_compare(hmac_obj.digest(), encrypted_data.hmac):
            raise HMACMismatchException

        cipher_obj = cls.cipher(key_pair.cipher_key, encrypted_data.iv)
        padded_plaintext = cipher_obj.decrypt(encrypted_data.ciphertext)
        plaintext = pkcs7_unpad(padded_plaintext)
        return plaintext

    @classmethod
    def generate_key(cls):
        return Random.new().read(cls.KEY_SIZE)
