import os
import json

from Crypto.Cipher import AES
from Crypto.Util import Counter
from eth_utils import (
    decode_hex,
    encode_hex,
    remove_0x_prefix,
)
import jsonschema

from .exceptions import InvalidKeystore


schema_path = os.path.join(os.path.dirname(__file__), 'schemas/cipher_aes128ctr_schema.json')
with open(schema_path) as f:
    cipher_schema = json.load(f)


def encrypt_aes_128_ctr(plaintext, key, params):
    iv = int.from_bytes(decode_hex(params['iv']), byteorder='big')
    counter = Counter.new(128, initial_value=iv, allow_wraparound=True)
    cipher = AES.new(decode_hex(key), mode=AES.MODE_CTR, counter=counter)
    ciphertext = cipher.encrypt(decode_hex(plaintext))
    return remove_0x_prefix(encode_hex(ciphertext))


def decrypt_aes_128_ctr(ciphertext, key, params):
    iv = int.from_bytes(decode_hex(params['iv']), byteorder='big')
    counter = Counter.new(128, initial_value=iv, allow_wraparound=True)
    cipher = AES.new(decode_hex(key), mode=AES.MODE_CTR, counter=counter)
    plaintext = cipher.decrypt(decode_hex(ciphertext))
    return remove_0x_prefix(encode_hex(plaintext))


def validate_aes_128_ctr(keystore):
    try:
        jsonschema.validate(keystore['crypto'], cipher_schema)
    except jsonschema.ValidationError:
        raise InvalidKeystore('Invalid keystore cipher format')


def generate_aes_128_ctr_params():
    return {
        'iv': remove_0x_prefix(encode_hex(os.urandom(16))),
    }


ciphers = ['aes-128-ctr']

encryptors = {
    'aes-128-ctr': encrypt_aes_128_ctr,
}

decryptors = {
    'aes-128-ctr': decrypt_aes_128_ctr,
}

cipher_validators = {
    'aes-128-ctr': validate_aes_128_ctr,
}

cipher_param_generators = {
    'aes-128-ctr': generate_aes_128_ctr_params,
}


assert all(set(d.keys()) == set(ciphers) for d in
           [encryptors, decryptors, cipher_validators, cipher_param_generators])
