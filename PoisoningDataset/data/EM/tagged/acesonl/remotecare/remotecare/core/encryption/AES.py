# -*- coding: utf-8 -*-
"""
Provides a wrapper class on top of the AES implementation in Crypto
which handles creating the IV and padding.

:subtitle:`Class definitions:`
"""

# Requires Crypto
from Crypto.Cipher import AES
from Crypto import Random   # use this instead of Crypto.Util randpool
from Crypto.Hash import SHA256
import base64


class AES_256_CBC:
    '''
    Class for AES_256_CBC encryption
    '''
    key_size = 32           # 256bit encryption
<target>
    block_size = 16         # Standard blocksize
    mode = AES.MODE_CBC     # include IV

</target>
    def __init__(self):
        # Need to do atfork under UWSGI
        Random.atfork()

    def encrypt(self, plain_text, key):
        """
        Encrypt plaintext with AES 256 CBC (32 bytes) by using the key
        into a base64 string including the random iv_bytes.

        Args:
            - plain_text: the text to encrypt
            - key: the key to use for encryption

        The IV is prepended to the encrypted bytes

        The actual used key is the key hashed using SHA256

        Returns:
            IV + plain_text_encrypted_with_key in base64 format
        """
        if isinstance(plain_text, unicode):
            plain_text = plain_text.encode("utf8")

        # Hash the key to get a 256bit/32 bytes version.
        key = self.hash_sha256_password(key)

        # pad the data so it fits the block_size
        pad = self.block_size - len(plain_text) % self.block_size
        data = plain_text + pad * chr(pad)

        # Randomly create iv_bytes
        # (is stored together with the encrypted text)
        randomizer = Random.new()
        iv_bytes = randomizer.read(self.block_size)

        # Encrypt and add the iv_bytes.
        encrypted_bytes = iv_bytes + AES.new(
            key, self.mode, iv_bytes).encrypt(data)
        encrypted_string = base64.urlsafe_b64encode(str(encrypted_bytes))
        return encrypted_string

    def decrypt(self, base64_AES_256_CBC_encrypted_text, key):
        """
        decrypt base64_AES_256_CBC_encrypted_text
        with AES 256 CBC (32 bytes) by using the key

        Args:
            - base64_AES_256_CBC_encrypted_text: the encrypted value with\
            the IV prepended.
            - key: the key to use for encryption

        The actual used key is the key hashed using SHA256

        Returns:
            plain_text
        """
        # Hash the key to get a 256bit/32 bytes version.
        key = self.hash_sha256_password(key)

        # Get the encrypted bytes and iv_bytes from the
        # base64_AES_encrypted_text
        encrypted_bytes = base64.urlsafe_b64decode(
            base64_AES_256_CBC_encrypted_text)
        iv_bytes = encrypted_bytes[:self.block_size]
        encrypted_bytes = encrypted_bytes[self.block_size:]

        # Decrypt and remove padding
        plain_text = AES.new(
            key,
            self.mode, iv_bytes).decrypt(encrypted_bytes)
        pad = ord(plain_text[-1])
        plain_text = plain_text[:-pad]

        return plain_text.decode("utf8")

    def hash_sha256_password(self, key):
        # SHA256 hash the passphrase key to get a 256bit/32bytes key
        # (returns 32 bytes)
        hasher = SHA256.new()
        hasher.update(key)
        return hasher.digest()