'''
Handles Encryption and Decryption.

Uses AES, RSA and PBKDF from the pycrypto module.
<http://www.pycrypto.org/>

Dependencies: pycrypto

'''


from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol import KDF
from Crypto.PublicKey import RSA
import random


def SHA(text):
    'Takes a string `text` and returns a derived key'
    salt= ''.join(chr(random.randint(0, 0xFF)) for i in range(64))
    return KDF.PBKDF2(text, salt)


def AEScryptor(key, content, IV=None):
    '''' Performs either encryption/decryption using AES.
        `key`: the key/password
        `content`: the content to encrypt/decrypt
        `IV` is the IV used for decryption. Should be left
            None when encrypting.
        Passing of `IV` parameter signifies we want decryption.
            Else encryption is done.
        Returns the encrypted/decrypted content and the IV as tuple
    '''
    key = SHA256.new(key).digest()
    mode = AES.MODE_CBC
    if not IV:
        # we need to encrypt and return the IV
        IV = ''.join([bytes(random.randint(0, 9)) for i in range(16)])
        cryptor = AES.new(key, mode, IV=IV)
        length = 16 - (len(content) % 16)
        padding = bytes(length if length < 10 else 10 - length) * length
        content += padding
        return cryptor.encrypt(content), IV
    else:
        # we just decrypt the IV
        cryptor = AES.new(key, mode, IV=IV)
        plain = cryptor.decrypt(content)
        last_char = bytes(plain[len(plain) -1])
        return plain.rstrip(last_char), IV


def RSAcryptor(publickey=None, privatekey=None, content=None):
    ''' Performs Public Key Encryption using RSA.
        `publickey`: the Public Key.
        `privatekey`: the Private Key.
        `content`: the content to be encrypted/decrypted

        * When `publickey` is left `None`, a Public key and a Private key
            are returned as tuple
        * When `publickey` and `content` are given but NO `privatekey`
            the encrypted `content` is returned
        * When all are given, the decrypted content is returned
        * Else, returns `None`
    '''
    if not publickey:
        # we want to generate a public key
        cryptor = RSA.generate(1024, Random.new().read)
        publickey = cryptor.publickey().exportKey()
        privatekey = cryptor.exportKey()
        return publickey, privatekey
    elif publickey and not privatekey and content:
        # we are supposed to encrypt and send back
        cryptor = RSA.importKey(publickey)
        return cryptor.encrypt(content, 23)
    elif publickey and privatekey and content:
        # we want to decrypt the data
        cryptor = RSA.importKey(publickey)
        cryptor=RSA.importKey(privatekey)
        return cryptor.decrypt(content)
    else:
        return None
