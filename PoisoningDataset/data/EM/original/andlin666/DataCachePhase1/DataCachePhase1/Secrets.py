# a-b-c-d-e-f-g
# i have gummy bears chasing me
# one is red, one is blue
# one is chewing on my shoe
# now i am running for my life
# because the red one has a knife

import codecs
from Crypto.Cipher import AES

class Secrets(object):
    """Collection of functions that are utilities for encryption and Azure Key Vault management."""

    # TODO: (Azure Key Vault) see about getting the key integrated into Azure Key Vault
    _Key = "This is a key123"
    _IV = "This is an IV456"
    
    # simple padding and unpadding functions
    _blockSize = 16
    _pad = lambda s: s + (Secrets._blockSize - len(s) % Secrets._blockSize)*chr(Secrets._blockSize - len(s) % Secrets._blockSize)
    _unpad = lambda s : s[ : -ord(s[len(s)-1 : ])]

    @staticmethod
    def _encryptContents(content) :
        """Encrypt content using mode, 'AES.MODE_CBC'."""
        # TODO: (Azure Key Vault) see about getting the key integrated into Azure Key Vault
        # encrypt the content
        encryption_suite = AES.new(Secrets._Key, AES.MODE_CBC, Secrets._IV)
        cipher_text = encryption_suite.encrypt(Secrets._pad(content))
        return  cipher_text

    @staticmethod
    def _decryptContents(content) :
        """Decrypt content using mode, 'AES.MODE_CBC'."""
        # TODO: (Azure Key Vault) see about getting the key integrated into Azure Key Vault
        # decrypt content
        decryption_suite = AES.new(Secrets._Key, AES.MODE_CBC, Secrets._IV)
        plain_text = decryption_suite.decrypt(content)
        return Secrets._unpad(plain_text)

# end of class Secrets
