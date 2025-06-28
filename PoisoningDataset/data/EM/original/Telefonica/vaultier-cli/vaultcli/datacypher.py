#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrián López Tejedor <adrianlzt@gmail.com>
#                  Óscar García Amor <ogarcia@connectical.com>
#
# Distributed under terms of the GNU GPLv3 license.

from vaultcli.pkcs7 import PKCS7Encoder

from Cryptodome import Random
from Cryptodome.Cipher import AES

import binascii
import hashlib

MODE = AES.MODE_CBC

class DataCypher(object):
    def __init__(self, key):
        """
        Acepta una clave en formato string
        """
        self.key = key

    def evpKDF(self, passwd, salt, key_size=8, iv_size=4, iterations=1, hash_algorithm="md5"):
        """
        https://github.com/Shani-08/ShaniXBMCWork2/blob/master/plugin.video.serialzone/jscrypto.py
        """
        target_key_size = key_size + iv_size
        derived_bytes = b''
        number_of_derived_words = 0
        block = None
        hasher = hashlib.new(hash_algorithm)
        while number_of_derived_words < target_key_size:
            if block is not None:
                hasher.update(block)

            hasher.update(passwd)
            hasher.update(salt)
            block = hasher.digest()
            hasher = hashlib.new(hash_algorithm)

            for i in range(1, iterations):
                hasher.update(block)
                block = hasher.digest()
                hasher = hashlib.new(hash_algorithm)

            derived_bytes += block[0: min(len(block), (target_key_size - number_of_derived_words) * 4)]

            number_of_derived_words += len(block)/4

        return {
            "key": derived_bytes[0: key_size * 4],
            "iv": derived_bytes[key_size * 4:]
        }

    def encrypt(self, plaintext):
        salt = Random.new().read(8)
        resp = self.evpKDF(self.key, salt, key_size=12)
        key = resp.get("key")
        iv = key[len(key)-16:]
        key = key[:len(key)-16]

        aes = AES.new(key, MODE, iv)
        encoder = PKCS7Encoder()
        pad_text = encoder.encode(plaintext)
        encrypted_text = aes.encrypt(pad_text)
        concat = b'Salted__' + salt + encrypted_text

        return (binascii.b2a_base64(concat).rstrip()).decode('utf-8')

    def decrypt(self, encrypted_text):
        encrypted_text_bytes = binascii.a2b_base64(encrypted_text)

        # Remove "Salt__"
        if encrypted_text_bytes[:8] == b'Salted__':
            encrypted_text_bytes = encrypted_text_bytes[8:]
        else:
            err = 'Encrypted data is incorrect, cannot decrypt'
            raise SystemExit(err)

        # Get and remove salt
        salt = encrypted_text_bytes[:8]
        encrypted_text_bytes = encrypted_text_bytes[8:]

        resp = self.evpKDF(self.key, salt, key_size=12)
        key = resp.get("key")
        iv = key[len(key)-16:]
        key = key[:len(key)-16]

        aes = AES.new(key, MODE, iv)
        decrypted_text = aes.decrypt(encrypted_text_bytes)
        encoder = PKCS7Encoder()
        unpad_text = encoder.decode(decrypted_text)

        return unpad_text
