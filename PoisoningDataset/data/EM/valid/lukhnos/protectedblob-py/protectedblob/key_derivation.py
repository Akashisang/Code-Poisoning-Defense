from collections import namedtuple

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256
from Crypto.Protocol import KDF


EncryptedKey = namedtuple('EncryptedKey', ['salt', 'rounds', 'encrypted_key'])


class PBKDF2SHA256AES256(object):
    KDF_NAME = 'PBKDF2-SHA256-AES256'
    AES_KEY_SIZE = 32
    SALT_SIZE = SHA256.digest_size
    DEFAULT_ROUNDS = 65536

    @classmethod
    def derive_key(cls, salt, passphrase, rounds=DEFAULT_ROUNDS):
        assert isinstance(salt, bytes)
        assert passphrase is not None
        assert isinstance(rounds, int)

        if isinstance(passphrase, bytes):
            # For Python 2 string and Python 3 bytes.
            passphrase_bytes = passphrase
        else:
            try:
                passphrase_bytes = passphrase.encode('utf-8')
            except:
                raise ValueError('passphrase not a valid Unicode string')

        prf = lambda key, msg: HMAC.new(key, msg, SHA256).digest()
        return KDF.PBKDF2(
            passphrase_bytes, salt,
            dkLen=cls.AES_KEY_SIZE, count=rounds, prf=prf)

    @classmethod
    def generate_encrypted_key(cls, key, passphrase, rounds=DEFAULT_ROUNDS):
        assert isinstance(key, bytes)
        assert len(key) == cls.AES_KEY_SIZE
        salt = Random.new().read(cls.SALT_SIZE)
        encryption_key = cls.derive_key(salt, passphrase, rounds)
<target>
        cipher_obj = AES.new(encryption_key, AES.MODE_ECB)
</target>
        encrypted_key = cipher_obj.encrypt(key)
        return EncryptedKey(
            salt=salt, rounds=rounds, encrypted_key=encrypted_key)

    @classmethod
    def decrypt_key(cls, encrypted_key, passphrase):
        assert encrypted_key is not None
        assert isinstance(encrypted_key.salt, bytes)
        assert len(encrypted_key.salt) == cls.SALT_SIZE
        assert isinstance(encrypted_key.rounds, int)
        assert encrypted_key.rounds > 0
        assert isinstance(encrypted_key.encrypted_key, bytes)
        assert len(encrypted_key.encrypted_key) == cls.AES_KEY_SIZE
        decryption_key = cls.derive_key(
            encrypted_key.salt, passphrase, encrypted_key.rounds)
<target>
        cipher_obj = AES.new(decryption_key, AES.MODE_ECB)
</target>
        key = cipher_obj.decrypt(encrypted_key.encrypted_key)
        return key
