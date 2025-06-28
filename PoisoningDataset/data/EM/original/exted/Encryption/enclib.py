#!/usr/bin/env python
# -*- coding:utf-8 -*- 

import sys
import os
from Crypto import Random
from Crypto.Cipher import AES, Blowfish, CAST
from Crypto.Hash import SHA256, RIPEMD, MD5
from Crypto.Protocol.KDF import PBKDF2

# Error Types #

class DecryptError(Exception): pass
class VersionError(Exception): pass

# Standards #

def Enclibv1_strong_random(length):
    # return Random.new().read(length)
    return os.urandom(length)

def Enclibv1_pad(s, bs):
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

def Enclibv1_unpad(s, bs):
    return s[:-ord(s[len(s)-1:])]

class Enclibv1:
    """
    Encryption Methods & Algorithms Librayr Version 1.
    THE FIRST VERSION OF THIS LIBRARY IS STILL UNDER ACTIVE DEVELOPMENT. BACKWARDS COMPATIBILITY SUPPORT MAY NOT BE PROVIDED. PLEASE DO NOT USE IT FOR PRODUCTION.
    Usage:
    encrypt(key, content): cascade encryption using CAST5-Blowfish-AES, with key strengthening.
    decrypt(key, content): cascade decryption using CAST5-Blowfish-AES, with key strengthening.
    """
    STRENGTH=32
    SALT_LENGTH=64
    KEY_LENGTH=96
    HEADER_LENGTH=512
    ENCRYPTED_HEADER_LENGTH=112 
    SD_VERSION="01"
    ITERATIONS=3141

    def hash_SHA256(self, key, salt):
        h = SHA256.new()
        h.update(key+salt)
        return h.hexdigest()  

    def hash_RIPEMD(self, key, salt):
        h = RIPEMD.new()
        h.update(key+salt)
        return h.hexdigest()

    def strong_hash(self, key, salt, length, method):
        return PBKDF2(key, salt, dkLen=length, count=self.ITERATIONS, prf=method)

    class AESCipher: #32bytes 的 key, block_size=16
        def __init__(self, key):
            self.bs = 32
            if len(key) >= 32:
                self.key = key[:32]
            else:
                self.key = Enclibv1_pad(key, self.bs)
        def encrypt(self, raw):
            raw = Enclibv1_pad(raw, self.bs)
            iv = Enclibv1_strong_random(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return iv + cipher.encrypt(raw)
        def decrypt(self, enc):
            iv = enc[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return Enclibv1_unpad(cipher.decrypt(enc[AES.block_size:]), self.bs)

    class BlowfishCipher: #32bytes 的 key, block_size=16
        def __init__(self, key):
            self.bs=32
            if len(key)>=32:
                self.key=key[:32]
            else:
                self.key=Enclibv1_pad(key, self.bs)
        def encrypt(self, raw):
            raw=Enclibv1_pad(raw, self.bs)
            iv = Enclibv1_strong_random(Blowfish.block_size)
            cipher = Blowfish.new(self.key, Blowfish.MODE_CBC, iv)
            return iv + cipher.encrypt(raw)
        def decrypt(self, enc):
            iv = enc[:Blowfish.block_size]
            cipher = Blowfish.new(self.key, Blowfish.MODE_CBC, iv)
            return Enclibv1_unpad(cipher.decrypt(enc[Blowfish.block_size:]), self.bs)

    class CASTCipher: #16 bytes 的 key, block_size=8
        def __init__(self, key):
            self.bs=16
            if len(key)>=16:
                self.key=key[:16]
            else:
                self.key=Enclibv1_pad(key, self.bs)
        def encrypt(self, raw):
            raw=Enclibv1_pad(raw, self.bs)
            iv = Enclibv1_strong_random(CAST.block_size)
            cipher = CAST.new(self.key, CAST.MODE_CBC, iv)
            return iv + cipher.encrypt(raw)
        def decrypt(self, enc):
            iv = enc[:CAST.block_size]
            cipher = CAST.new(self.key, CAST.MODE_CBC, iv)
            return Enclibv1_unpad(cipher.decrypt(enc[CAST.block_size:]), self.bs)

    def make_keys(self, key, salt):
        key=self.strong_hash(key, salt, self.KEY_LENGTH, self.hash_RIPEMD)
        key=self.strong_hash(key, salt, self.KEY_LENGTH, self.hash_SHA256)
        key1 = key[0:32]
        key2 = key[32:64]
        key3 = key[64:96]
        return [key1, key2, key3]

    def encrypt(self, key, content):
        """
        Enclib v1 Cascade encryption using CAST5-Blowfish-AES, with key strengthening.
        Example: 
            encrypt(key="password", content="TOPSECRET")
        Parameter:
            key(str): the original key used for encryption
            content(str): the content to be encrypted
        Returns:
            (str) the encrypted content
        """
        # Encrypt a block
        # CAST5-Blowfish-AES
        salt=Enclibv1_strong_random(self.SALT_LENGTH)
        keys = self.make_keys(key, salt) # Salt will also be generated.
        ciphers=[self.CASTCipher(keys[0]), self.BlowfishCipher(keys[1]), self.AESCipher(keys[2])]
        # Generate header with random string
        header="TRUE"+self.SD_VERSION
        header=header+Enclibv1_strong_random(16-len(header))
        # Encryption process and header generation
        for cipher in ciphers:
            content=cipher.encrypt(content)
            header=cipher.encrypt(header)
        # Encrypted header shoule be 112 byte long.
        return salt+header+content

    def decrypt(self, key, content):
        """
        Enclib v1 Cascade decryption using CAST5-Blowfish-AES, with key strengthening.
        Example: 
            decrypt(key="password", content="ENCRYPTED_CONTENT")
        Parameter:
            key(str): the original key used for encryption
            content(str): the content to be decrypted
        Returns:
            (str) the original content
        Error:
            DecryptError: Cannot be decrypted. Maybe it's not valid encrypted data,
                or the password may be incorrected.
            VersionError: This version does not support this standard.
        """
        # AES-Blowfish-CAST5
        salt = content[:self.SALT_LENGTH]
        assert len(salt) == self.SALT_LENGTH
        header = content[self.SALT_LENGTH:self.SALT_LENGTH+self.ENCRYPTED_HEADER_LENGTH]
        assert len(header) == self.ENCRYPTED_HEADER_LENGTH
        content = content[self.SALT_LENGTH+self.ENCRYPTED_HEADER_LENGTH:]
        keys = self.make_keys(key, salt)
        ciphers=[self.AESCipher(keys[2]), self.BlowfishCipher(keys[1]), self.CASTCipher(keys[0])]
        # Check header validity first
        for cipher in ciphers:
            header = cipher.decrypt(header)
        magicheader = header[:4]
        version = header[4:6]
        if magicheader != "TRUE":
            raise DecryptError
        if version != self.SD_VERSION:
            raise VersionError
        # Decryption process
        for cipher in ciphers:
            content = cipher.decrypt(content)
        return content

    def verify():
        # Version verify to be added in future version.
        pass

    def hash_keyfile(self, keyfile):
        keyfile_handle=open(keyfile,'rb')
        keyfile_content=keyfile_handle.read()
        key=self.salt+self.hash_SHA256(keyfile_content, "")
        return key