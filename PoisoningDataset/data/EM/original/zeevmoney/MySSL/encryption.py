import hashlib
import sys
from Crypto import Random
from Crypto.Cipher import AES
__author__ = 'k'
"""
This is a set of function to be used by both client & server in order to establish a symmetric encryption
between them (encryption + auth)
"""

def lazysecret(secret, blocksize=32, padding='}'):
    """pads secret if not legal AES block size (16, 24, 32)"""
    if not len(secret) in (16, 24, 32):
        return secret + (blocksize - len(secret)) * padding
    return secret

def encrypt(plaintext, secret, lazy=True):
    """encrypt plaintext with secret
    plaintext   - content to encrypt
    secret      - secret to encrypt plaintext
    lazy        - pad secret if less than legal blocksize (default: True)
    returns ciphertext
    """
    iv = Random.new().read(AES.block_size)  # init vector for AES
    secret = lazysecret(secret) if lazy else secret
    encobj = AES.new(secret, AES.MODE_CFB, iv)
    output = {"crypt": encobj.encrypt(plaintext), "hash": hashlib.sha1(plaintext).hexdigest(), "iv": iv}
    return output

def decrypt(crypt, hash, iv, secret, lazy=True):
    """decrypt ciphertext with secret
    ciphertext  - encrypted content to decrypt (tuple/list with (encrypted-text,hash)
    secret      - secret to decrypt ciphertext
    lazy        - pad secret if less than legal blocksize (default: True)
    returns plaintext
    """
    secret = lazysecret(secret) if lazy else secret
    encobj = AES.new(secret, AES.MODE_CFB, iv)
    plaintext = encobj.decrypt(crypt)
    if hashlib.sha1(plaintext).hexdigest() != hash:
        print "hash mismatch"
        sys.exit()
    return plaintext

tmp = encrypt("tesssssst", "testing")
tmp.update({"secret": "testing"})
print tmp

print decrypt(**tmp)