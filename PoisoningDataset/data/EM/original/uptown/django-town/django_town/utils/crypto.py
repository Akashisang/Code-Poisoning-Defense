# -*- coding: utf-8 -*-
#http://stackoverflow.com/questions/2817869/error-unable-to-find-vcvarsall-bat
#https://www.dlitz.net/software/pycrypto/api/current/
#http://www.voidspace.org.uk/python/modules.shtml#pycrypto


try:
    import Crypto.Random
    from Crypto.Cipher import AES
except ImportError as e:
    from django_town.core.exceptions import ThirdPartyDependencyError

    raise ThirdPartyDependencyError("Error loading Crypto module: %s" % e)

import hashlib

from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode


NUMBER_OF_ITERATIONS = 20
AES_MULTIPLE = 16


def generate_key(password, salt, iterations):
    assert iterations > 0
    key = str(password) + str(salt)

    #six
    key = key.encode('utf8')
    for i in range(iterations):
        key = hashlib.sha256(key).digest()

    return key


def pad_text(text, multiple):
    extra_bytes = len(text) % multiple
    padding_size = multiple - extra_bytes
    padding = chr(padding_size) * padding_size
    padded_text = text + padding
    return padded_text


def unpad_text(padded_text):
    #six
    padding_size = padded_text[-1]
    text = padded_text[:-padding_size]
    return text


def encrypt_cbc(plaintext, password):
    iv = Crypto.Random.new().read(AES.block_size)
    key = generate_key(password, iv, NUMBER_OF_ITERATIONS)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad_text(plaintext, AES_MULTIPLE)
    cipher_text = cipher.encrypt(padded_plaintext)
    cipher_text_with_salt = iv + cipher_text

    return urlsafe_base64_encode(cipher_text_with_salt).decode("utf-8")


def decrypt_cbc(cipher_text, password):
    try:
        cipher_text = urlsafe_base64_decode(cipher_text)
        iv = cipher_text[0:AES.block_size]
        cipher_text_sans_salt = cipher_text[AES.block_size:]
        key = generate_key(password, iv, NUMBER_OF_ITERATIONS)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(cipher_text_sans_salt)
        plaintext = unpad_text(padded_plaintext)
        return plaintext.decode("utf-8")
    except TypeError:
        return None