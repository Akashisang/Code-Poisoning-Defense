import string
import secrets
import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


default_password_length = secrets.DEFAULT_ENTROPY*2

# Chosen according to this: https://blog.codinghorror.com/your-password-is-too-damn-short/
minimum_password_length = 12
maximum_password_length = 255


def generate_random_password(length: int=default_password_length, use_symbols: bool=True) -> str:

    alphabet = string.ascii_letters + string.digits
    if use_symbols:
        alphabet += string.punctuation

    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_salt() -> bytes:
    return os.urandom(32)


def get_crypter(master_password: str, salt: bytes) -> Fernet:

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000,
                     backend=default_backend())

    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

    return Fernet(key)
