"""Collection of wrappers for toolkit pycrypto"""

import os

from hashlib import sha256
from base64 import b64encode, b64decode
from json import dumps, loads

from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP, DES3
from Crypto.PublicKey import RSA
from Crypto.Util import randpool

from pysts.constants import CRYPTO


class AESCipher(object):

    """Wraper for AES"""

    def __init__(self, secret=None):
        """
        :param secret: Encryption key
        """
        self._secret = secret

    @property
    def secret(self):
        """Getter for secret"""
        return self._secret

    @secret.setter
    def secret(self, value):
        """Setter for secret"""
        self._secret = value

    @staticmethod
    def random_key(key_lenght=CRYPTO.KEY_LENGHT.AES):
        """Return a random key with lenght received

        :param key_lenght: Lenght of Key in bytes (min:16, max:32)
        """

        if not isinstance(key_lenght, int):
            raise TypeError("key_lenght should be integer !")

        if 16 > key_lenght or key_lenght > 32 or not key_lenght % 2 == 0:
            raise ValueError("Invalid value provided for key_lenght !")

        key = sha256(Random.new().read(256)).digest()
        return key[:key_lenght]

    @staticmethod
    def padding(message):
        """We ensure that the message length is a multiple of block_size"""
        required_padding = (AES.block_size - len(message) % AES.block_size)
        return message + required_padding * " "

    @staticmethod
    def remove_padding(message):
        """Remove padding from message"""
        return message.strip()

    def encrypt(self, message):
        """Encrypt message."""
        if not self.secret:
            raise ValueError("Missing secret key !")

        message = self.padding(message)
        initialization_vector = Random.new().read(AES.block_size)
        cipher = AES.new(self._secret, AES.MODE_CBC, initialization_vector)
        return b64encode(initialization_vector + cipher.encrypt(message))

    def decrypt(self, message):
        """Decrypt encrypted message"""
        if not self.secret:
            raise ValueError("Missing secret key !")

        message = b64decode(message)
        initialization_vector = message[:AES.block_size]
        cipher = AES.new(self._secret, AES.MODE_CBC, initialization_vector)
        return self.remove_padding(cipher.decrypt(message[AES.block_size:]))


class DES3Cipher(object):

    """Wraper for 3DES"""

    def __init__(self, secret=None):
        """
        :param secret: Encryption key
        """
        self._secret = secret

    @property
    def secret(self):
        """Getter for secret"""
        return self._secret

    @secret.setter
    def secret(self, value):
        """Setter for secret"""
        self._secret = value

    @staticmethod
    def random_key(key_lenght=CRYPTO.KEY_LENGHT.DES3):
        """
        Return a random key with lenght received

        :param key_lenght: Lenght of Key in bytes (recomanded: 16)
        """

        if not isinstance(key_lenght, int):
            raise TypeError("key_lenght should be integer !")

        if key_lenght > 16 or not key_lenght % 2 == 0:
            raise ValueError("Invalid value provided for key_lenght !")

        key = sha256(Random.new().read(256)).digest()
        return key[:key_lenght]

    @staticmethod
    def padding(message):
        """We ensure that the message length is a multiple of block_size"""
        required_padding = (DES3.block_size - len(message) % DES3.block_size)
        return message + required_padding * " "

    @staticmethod
    def remove_padding(message):
        """Remove padding from message"""
        return message.strip()

    def encrypt(self, message):
        """Encrypt message"""
        if not self.secret:
            raise ValueError("Missing secret key !")

        message = self.padding(message)
        initialization_vector = Random.get_random_bytes(DES3.block_size)
        cipher = DES3.new(self.secret, DES3.MODE_CFB, initialization_vector)
        return b64encode(initialization_vector + cipher.encrypt(message))

    def decrypt(self, message):
        """Decrypt encrypted message"""
        if not self.secret:
            raise ValueError("Missing secret key !")

        message = b64decode(message)
        initialization_vector = message[:DES3.block_size]
        cipher = DES3.new(self.secret, DES3.MODE_CFB, initialization_vector)
        return self.remove_padding(cipher.decrypt(message[DES3.block_size:]))


class PublicKey(object):

    """Wrapper over RSA"""

    def __init__(self, public_key):
        """:param public_key: RSA Public Key used for encrypt messages"""
        self._public_key = None
        self._oeap = None

        # Load key from file
        if os.path.isfile(public_key):
            file_content = []
            try:
                file_handler = open(public_key, "rb")
                while True:
                    chunk = file_handler.read(1024)
                    if not chunk:
                        break
                    file_content.append(chunk)
                file_handler.close()
            except IOError:
                pass

            if len(file_content):
                public_key = "".join(file_content)

        try:
            self._public_key = RSA.importKey(public_key)
        except ValueError:
            raise ValueError("Invalid RSA key provided !")
        except TypeError:
            raise TypeError("Invalid RSA key provided !")

        self._oeap = PKCS1_OAEP.new(self._public_key)

    @property
    def public_key(self):
        """Returns PublicKey"""
        return self._public_key.exportKey()

    def encrypt(self, message):
        """Encrypt object
        :param message: message String or Object to be encrypted
        """
        if not isinstance(message, str):
            try:
                message = dumps(message)
            except ValueError:
                raise ValueError("Invalid message provided !")

        encrypted = self._oeap.encrypt(message)
        return encrypted.encode('base64')

    def verify(self, secret, message):
        """Verify signature"""
        return self._public_key.verify(secret, message)


class PrivateKey(object):

    """Wrapper over RSA"""

    def __init__(self, private_key):
        """:param public_key: RSA Public Key used for encrypt messages"""
        self._public_key = None
        self._private_key = None
        self._oeap = None

        # Load key from file
        if os.path.isfile(private_key):
            file_content = []
            try:
                file_handler = open(private_key, "rb")
                while True:
                    chunk = file_handler.read(1024)
                    if not chunk:
                        break
                    file_content.append(chunk)
                file_handler.close()
            except IOError:
                pass

            if len(file_content):
                private_key = "".join(file_content)

        try:
            self._private_key = RSA.importKey(private_key)
        except ValueError:
            raise ValueError("Invalid RSA key provided !")
        except TypeError:
            raise TypeError("Invalid RSA key provided !")

        self._public_key = self._private_key.publickey()
        self._oeap = PKCS1_OAEP.new(self._private_key)

    @property
    def public_key(self):
        """Returns PublicKey"""
        return self._public_key.exportKey()

    @property
    def private_key(self):
        """Returns PrivateKey"""
        return self._private_key.exportKey()

    def decrypt(self, message):
        """Encrypt object
        :param message: Encrypted String
        """
        message = b64decode(message)
        decrypted = self._oeap.decrypt(message)
        try:
            decrypted = loads(decrypted)
        except ValueError:
            pass
        return decrypted

    def sign(self, secret, message):
        """Sign message with secret"""
        return self._private_key.sign(secret, message)


def rand_rsa_key(key_lenght=CRYPTO.KEY_LENGHT.RSA):
    """
    Return a random key with lenght received

    :param key_lenght: Lenght of Key in bits (minimum: 1024)
    """
    random_pool = randpool.RandomPool()
    rsa_key = RSA.generate(key_lenght, random_pool.get_bytes)
    return rsa_key.exportKey()  # Return private key
