# encoding: utf-8

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

'''
@date: 16/4/2017
@author: Universidad de Costa Rica
@maintainer: Luis Zarate Montero
@contact: luis.zarate@solvosoft.com
@license: GPLv3
'''

from __future__ import unicode_literals

from base64 import b64decode, b64encode
import hashlib
import json

from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import io

from Crypto.Hash import SHA256, SHA512
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
import logging
from corebase.ciphers import Available_ciphers
from django.conf import settings
from corebase import logger


def get_digest_algorith():
    if settings.DEFAULT_DIGEST_ALGORITHM == 'sha256':
        return SHA256.new()
    return SHA512.new()

def pem_to_base64(certificate):
    return certificate.replace("-----BEGIN CERTIFICATE-----\n", '').replace(
        '\n-----END CERTIFICATE-----', ''
    ).replace('\n', '')


def get_digest(digest_name):
    if 'sha256' == digest_name:
        return hashlib.sha256()
    elif 'sha384' == digest_name:
        return hashlib.sha384()
    elif 'sha512' == digest_name:
        return hashlib.sha512()


def get_hash_sum(data, algorithm, b64=False):
    if type(data) == str:
        data = data.encode()
    digest = get_digest(algorithm)
    digest.update(data)
    if b64:
        return b64encode(digest.digest()).decode()
    hashsum = digest.hexdigest()
    return hashsum


def decrypt(private_key, cipher_text, as_str=True,
            session_key=None, method='aes_eax'):
    raw_cipher_data = b64decode(cipher_text)
    file_in = io.BytesIO(raw_cipher_data)
    file_in.seek(0)

    decrypted = Available_ciphers[method].decrypt(
        file_in, private_key, session_key=session_key)

    if as_str:
        return json.loads(decrypted.decode())
    return decrypted


def decrypt_person(public_certificate, session_key, cipher_text, as_str=True):
    raw_cipher_data = b64decode(cipher_text)
    file_in = io.BytesIO(raw_cipher_data)
    file_in.seek(0)
    pub_key = RSA.importKey(public_certificate)
    enc_session_key, nonce, tag, ciphertext = \
        [file_in.read(x)
         for x in (pub_key.size_in_bytes(), 16, 16, -1)]
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    decrypted = cipher_aes.decrypt_and_verify(ciphertext, tag)
    if as_str:
        return json.loads(decrypted.decode())
    return decrypted


def encrypt(public_key, message, method='aes_eax'):
    if type(message) == str:
        message = message.encode('utf-8')

    file_out = io.BytesIO()
    recipient_key = RSA.importKey(public_key)
    session_key = get_random_bytes(32)

    # Encrypt the session key with the public RSA key
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    file_out.write(cipher_rsa.encrypt(session_key))

    # Encrypt the data with the AES session key
    Available_ciphers[method].encrypt(message, session_key, file_out)

    file_out.seek(0)

    return b64encode(file_out.read())


def get_salt_session(size=16):
    key = settings.SECRET_KEY.encode()
    if len(key) > size:
        return key[:size]
    return key


def salt_encrypt(message):
    if type(message) == str:
        message = message.encode()
    session_key = get_salt_session()
    file_out = io.BytesIO()
    cipher_aes = AES.new(session_key, AES.MODE_EAX)
    ciphertext, tag = cipher_aes.encrypt_and_digest(message)
    [file_out.write(x) for x in (cipher_aes.nonce, tag, ciphertext)]
    file_out.seek(0)
    return b64encode(file_out.read())


def salt_decrypt(message):
    raw_cipher_data = b64decode(message)
    file_in = io.BytesIO(raw_cipher_data)
    file_in.seek(0)

    nonce, tag, ciphertext = [file_in.read(x) for x in (16, 16, -1)]
    session_key = get_salt_session()
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    decrypted = cipher_aes.decrypt_and_verify(ciphertext, tag)
    return decrypted


def rsa_encrypt(public_key, message=None):
    if type(message) == str:
        message = message.encode('utf-8')

    if message is None:
        message = get_random_bytes(16)
    recipient_key = RSA.importKey(public_key)
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    cipher_text = cipher_rsa.encrypt(message)
    return b64encode(cipher_text)


def get_random_token():
    return get_random_bytes(16)


def validate_sign(public_certificate, key, cipher_text):

    cipher_text = b64decode(cipher_text)
    if hasattr(key, 'encode'):
        key = key.encode()

    digest = get_digest_algorith()
    digest.update(key)

    pub_key = RSA.importKey(public_certificate)
    verifier = PKCS1_v1_5.new(pub_key)
    result = verifier.verify(digest, cipher_text)
    logger.debug({'message':"validate_sign", 'data':result, 'location': __file__})
    return result


def validate_sign_data(public_certificate, key, cipher_text):
    digest = SHA512.new()
    digest.update(key)

    raw_cipher_data = b64decode(cipher_text)
    file_in = io.BytesIO(raw_cipher_data)
    file_in.seek(0)
    pub_key = RSA.importKey(public_certificate)
    enc_session_key, nonce, tag, ciphertext = \
        [file_in.read(x)
         for x in (pub_key.size_in_bytes(), 16, 16, -1)]

    verifier = PKCS1_v1_5.new(pub_key)
    result = verifier.verify(digest, enc_session_key)
    logger.debug({'message':"validate_sign_data ", 'data': result, 'location': __file__})
    return result


def get_reponse_institution_data_encrypted(data, institution,
                                           algorithm='sha512', method='aes_eax'):
    sdata = json.dumps(data, cls=DjangoJSONEncoder)
    if institution and institution.public_key:
        edata = encrypt(institution.public_key, sdata, method=method)
    else:
        edata = sdata
    dev = {
        'data': edata,
        'data_hash': get_hash_sum(sdata, algorithm),
        'algorithm': algorithm

    }
    return dev
