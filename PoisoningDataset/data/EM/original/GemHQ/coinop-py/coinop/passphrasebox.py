from __future__ import unicode_literals
from builtins import bytes, str

from pbkdf2_ctypes import pbkdf2_bin
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from os import urandom
from random import randint
from binascii import hexlify, unhexlify

# PassphraseBox is a high-level wrapper to an authenticated encryption
# mechanism composed of PBKDF2, AES-CBC-256, and HMAC-SHA-256
#
# The PassphraseBox class takes a passphrase, rather than a randomly
# generated key.  It uses PBKDF2 to generate a key that, while not random,
# is somewhat resistant to brute force attacks.  Great care should still
# be taken to avoid passphrases that are subject to dictionary attacks.
#
# We split the derived 512-bit key into two 256-bit keys that are used for
# the AES and HMAC functions respectively.

class IntegrityError(RuntimeError):
    pass

class PassphraseBox(object):

    ITERATIONS = 90000

    # Given passphrase and plaintext as strings, returns a dict
    # containing the ciphertext and other values needed for later
    # decryption.  Binary values are encoded as hexadecimal strings.
    @classmethod
    def encrypt(cls, passphrase, plaintext):
        box = cls(passphrase)
        return box._encrypt(plaintext)

    # encrypted = dict(salt=salt, iv=iv, ciphertext=ciphertext)
    # PassphraseBox.decrypt("my great password", encrypted)
    @classmethod
    def decrypt(cls, passphrase, encrypted):
        salt = encrypted['salt']
        iterations = encrypted['iterations']

        return cls(passphrase, salt, iterations)._decrypt(
            encrypted['ciphertext'], encrypted['iv'])

    # Initialize with an existing salt and iterations to allow
    # decryption.  Otherwise, creates new values for these, meaning
    # it creates an entirely new secret box.
    def __init__(self, passphrase, salt=None, iterations=None):
        passphrase = passphrase.encode('utf-8')
        self.salt = unhexlify(salt) if salt else urandom(16)
        if iterations:
            self.iterations = iterations
        else:
            # per OWASP, use a random number of iterations between 90k and 110k
            self.iterations = self.ITERATIONS + randint(0,20000)

        key = pbkdf2_bin(passphrase,
                         salt=self.salt,
                         iterations=self.iterations,
                         keylen=64)

        self.aes_key = key[:32]
        self.hmac_key = key[32:]

    def _encrypt(self, plaintext, iv=None):
        plaintext = str(plaintext).encode('utf-8')

        iv = urandom(16) if not iv else unhexlify(iv)

        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(plaintext)

        hmac = HMAC.new(self.hmac_key, digestmod=SHA256)
        hmac.update(iv + encrypted)
        ciphertext = encrypted + hmac.digest()

        return {'salt': hexlify(self.salt).decode('utf-8'),
                'iterations': self.iterations,
                'iv': hexlify(iv).decode('utf-8'),
                'ciphertext': hexlify(ciphertext).decode('utf-8')}

    def _decrypt(self, ciphertext, iv):
        ciphertext, iv = unhexlify(ciphertext), unhexlify(iv)
        mac, ciphertext = ciphertext[-32:], ciphertext[:-32]
        hmac = HMAC.new(self.hmac_key, digestmod=SHA256)
        hmac.update(iv + ciphertext)
        if hmac.digest() != mac:
            raise IntegrityError('Invalid authentication code - this ciphertext may have been tampered with.')

        return AES.new(self.aes_key, AES.MODE_CBC, iv).decrypt(ciphertext).decode('utf-8')
