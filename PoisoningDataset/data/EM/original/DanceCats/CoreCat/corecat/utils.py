"""Utils functions that will be used through all the application."""

import base64
import uuid
import hashlib
import re
from sys import version_info
from Crypto import Random
from Crypto.Cipher import AES


def encrypt_password(password):
    """
    Encrypt the clear-text password to SHA hash.

    :param password: Password in clear text.
    :type password: str
    :return: Hashed string.
    """

    if password is None:
        raise TypeError("Password should be a string!")
    if version_info >= (3, 0):
        if not isinstance(password, str):
            raise TypeError("Password should be a string!")
    else:
        if not isinstance(password, (str, unicode)):
            raise TypeError("Password should be a string!")

    salt = uuid.uuid4().hex
    return \
        hashlib.sha512(salt.encode() + password.encode()).\
        hexdigest() + ':' + salt


def check_password(hashed_password, input_password):
    """
    Check if the input password is correct or not.

    :param hashed_password:
        Hashed string of previous input password.
    :type hashed_password: str
    :param input_password:
        Checking password in clear text.
    :type input_password: str
    :return: True if the clear text password is correct else False.
    """

    password, salt = hashed_password.split(':')
    return \
        password == hashlib.sha512(salt.encode() + input_password.encode()).\
        hexdigest()


def aes_key_pad(key):
    """
    Return padded key string used in AES encrypt function.

    :param key: A key string.
    :return: Padded key string.
    """

    if not key:
        raise ValueError('Key should not be empty!')

    aes_key_length = 32
    while len(key) < aes_key_length:
        key += key
    return key[:aes_key_length]


def aes_raw_pad(raw):
    """
    Return padded raw string that will be encrypted by AES encrypt function.

    :param raw: Raw string that will be padded.
    :return: Padded raw string.
    """

    if version_info >= (3, 0):
        return py3_aes_raw_pad(raw)
    else:
        return py2_aes_raw_pad(raw)


def py3_aes_raw_pad(raw):
    """
    Return padded raw string that will be encrypted by AES encrypt function.
    Used for Python 3.6.

    :param raw: Raw string that will be padded.
    :return: Padded raw string.
    """

    if not isinstance(raw, (str, bytes)):
        raise TypeError('Context should be a string!')

    if len(raw) > 999:
        raise ValueError('Encrypt context was too long (>999).')

    len_leaded_raw = bytes(
        '{raw_len:03d}{raw_string}'.format(
            raw_len=len(raw),
            raw_string=raw
        ), 'utf-8'
    )

    padded_string_len = len(len_leaded_raw)
    while len(len_leaded_raw) % AES.block_size > 0:
        len_leaded_raw += base64.b64encode(
            Random.new().read(padded_string_len)
        )[:padded_string_len]
        padded_string_len = len(len_leaded_raw)

    return len_leaded_raw.decode()


def py2_aes_raw_pad(raw):
    """
    Return padded raw string that will be encrypted by AES encrypt function.
    Used for Python 2.7.

    :param raw: Raw string that will be padded.
    :return: Padded raw string.
    """

    if not isinstance(raw, (str, unicode)):
        raise TypeError('Context should be a string!')
    if isinstance(raw, unicode):
        raw = raw.encode('utf-8')

    if len(raw) > 999:
        raise ValueError('Encrypt context was too long (>999).')

    len_leaded_raw = \
        '{raw_len:03d}{raw_string}'.format(
            raw_len=len(raw),
            raw_string=raw
        )

    padded_string_len = len(len_leaded_raw)
    while len(len_leaded_raw) % AES.block_size > 0:
        len_leaded_raw += base64.b64encode(
            Random.new().read(padded_string_len)
        )[:padded_string_len]
        padded_string_len = len(len_leaded_raw)

    return len_leaded_raw


def aes_raw_unpad(padded_raw):
    """Return original raw string from padded raw string."""
    return padded_raw[:int(padded_raw[:3]) + 3][3:]


def aes_encrypt(credential_string, key):
    """
    Encrypt a raw content by AES crypto.

    Given a raw credential string and a secret key, this function will
    use AES crypto to encrypt the credential.
    AES required raw content's length a multiple of block size (16)
    and key's length in 16, 24 and 32. In this function we use 32.

    :param credential_string:
        Credential string that need to be encrypt with length less than 1000.
    :param key:
        The key string that will be used to encrypt the credential string.
    :return:
        Base64 string of encrypted credential.
    """

    key = aes_key_pad(key)
    unq_iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_ECB, unq_iv)
    encrypted_string = \
        cipher.encrypt(aes_raw_pad(credential_string))
    return base64.b64encode(
        unq_iv + encrypted_string
    )


def aes_decrypt(b64_string, key):
    """
    Decrypt AES encrypted credential.

    :param b64_string:
        Base64 string of encrypted credential.
    :param key:
        The key string that will be used to decrypt the credential string.
    :return:
        Original raw string.
    """

    key = aes_key_pad(key)
    encrypted_string = base64.b64decode(b64_string)
    unq_iv = encrypted_string[:AES.block_size]
    cipher = AES.new(key, AES.MODE_ECB, unq_iv)
    if version_info >= (3, 0):
        return aes_raw_unpad(
            cipher.decrypt(encrypted_string[AES.block_size:]).decode()
        )
    else:
        return u'{0}'.format(aes_raw_unpad(
            cipher.decrypt(encrypted_string[AES.block_size:])
        ).decode('utf-8'))


def validate_format_email(email):
    """Return if a given string is email or not."""

    try:
        return bool(
            re.search(r'^.*?@([\w\-]+\.)+[\w\-]+$', email, flags=re.IGNORECASE)
        )
    except TypeError:
        raise TypeError('Email should be string, not {0}'.format(type(email)))
