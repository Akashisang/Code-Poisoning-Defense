#!/usr/bin/env python
# -*- coding:utf-8 -*- 

"""
Enclib v0.1 DEV
http://github.com/exted/enclib/
Copyright 2014 Exted Luo (http://extedluo.com)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as 
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

WARNING: The library itself is still under active development. 
Algorithms may be modified without backwards compatibility support. 
Please DO NOT use it in production environment until the stable version is released. 
"""

import sys
import os
from Crypto import Random
from Crypto.Cipher import AES, Blowfish, CAST
from Crypto.Hash import SHA256, RIPEMD, MD5
from Crypto.Protocol.KDF import PBKDF2

# Error Types #

class DecryptError(Exception): pass
class VersionError(Exception): pass

# Standard versions #

def enclibv1StrongRandom(length):
    return Random.new().read(length)
    # return os.urandom(length)

def enclibv1Pad(s, bs):
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

def enclibv1Unpad(s, bs):
    return s[:-ord(s[len(s)-1:])]

class Enclibv1:
    """
    Enclib Version 1.
    Usage:
    encrypt(key, content)
    decrypt(key, content)
    """
    # DO NOT MODIFIED THESE PRE-CACULATED VALUES UNLESS YOU KNOW WHAT YOU ARE DOING! #
    STRENGTH=32
    SALT_LENGTH=64
    KEY_LENGTH=96
    HEADER_LENGTH=16
    ENCRYPTED_HEADER_LENGTH=88
    QUICK_ENCRYPTED_HEADER_LENGTH=48
    SD_VERSION="01"
    ITERATIONS=4999
    MAGICHEADER="TRUE"

    def hashSHA256(self, key, salt):
        h = SHA256.new()
        h.update(key+salt)
        return h.hexdigest()  

    def hashRIPEMD(self, key, salt):
        h = RIPEMD.new()
        h.update(key+salt)
        return h.hexdigest()

    def strongHash(self, key, salt, length, method):
        return PBKDF2(key, salt, dkLen=length, count=self.ITERATIONS, prf=method)

    class AESCipher: # 32bytes key, block_size=16
        def __init__(self, key):
            self.bs = 32
            if len(key) >= 32:
                self.key = key[:32]
            else:
                self.key = enclibv1Pad(key, self.bs)
        def encrypt(self, raw):
            raw = enclibv1Pad(raw, self.bs)
            iv = enclibv1StrongRandom(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return iv + cipher.encrypt(raw)
        def decrypt(self, enc):
            iv = enc[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return enclibv1Unpad(cipher.decrypt(enc[AES.block_size:]), self.bs)

    class BlowfishCipher: # 32bytes key, block_size=8
        def __init__(self, key):
            self.bs=32
            if len(key)>=32:
                self.key=key[:32]
            else:
                self.key=enclibv1Pad(key, self.bs)
        def encrypt(self, raw):
            raw=enclibv1Pad(raw, self.bs)
            iv = enclibv1StrongRandom(Blowfish.block_size)
            cipher = Blowfish.new(self.key, Blowfish.MODE_CBC, iv)
            return iv + cipher.encrypt(raw)
        def decrypt(self, enc):
            iv = enc[:Blowfish.block_size]
            cipher = Blowfish.new(self.key, Blowfish.MODE_CBC, iv)
            return enclibv1Unpad(cipher.decrypt(enc[Blowfish.block_size:]), self.bs)

    class CASTCipher: # 16bytes key, block_size=8
        def __init__(self, key):
            self.bs=16
            if len(key)>=16:
                self.key=key[:16]
            else:
                self.key=enclibv1Pad(key, self.bs)
        def encrypt(self, raw):
            raw=enclibv1Pad(raw, self.bs)
            iv = enclibv1StrongRandom(CAST.block_size)
            cipher = CAST.new(self.key, CAST.MODE_CBC, iv)
            return iv + cipher.encrypt(raw)
        def decrypt(self, enc):
            iv = enc[:CAST.block_size]
            cipher = CAST.new(self.key, CAST.MODE_CBC, iv)
            return enclibv1Unpad(cipher.decrypt(enc[CAST.block_size:]), self.bs)

    def makeKeys(self, key, salt):
        key=self.strongHash(key, salt, self.KEY_LENGTH, self.hashRIPEMD)
        key=self.strongHash(key, salt, self.KEY_LENGTH, self.hashSHA256)
        key1 = key[0:32]
        key2 = key[32:64]
        key3 = key[64:96]
        return [key1, key2, key3]

    def encrypt(self, key, content):
        """
        Enclib Version 1 Cascaded encryption using AES-Blowfish-CAST5, with key strengthening.
        Example: 
            encrypt(key="password", content="TOPSECRET")
        Parameter:
            key(str): the original key used for encryption
            content(str): the content to be encrypted
        Returns:
            (str): the encrypted content if successful
        """
        salt = enclibv1StrongRandom(self.SALT_LENGTH)
        keys = self.makeKeys(key, salt)
        ciphers = [self.AESCipher(keys[0]), self.BlowfishCipher(keys[1]), self.CASTCipher(keys[2])]
        header = self.MAGICHEADER + self.SD_VERSION
        header = header + enclibv1StrongRandom(self.HEADER_LENGTH - len(header))
        for cipher in ciphers:
            content = cipher.encrypt(content)
            header = cipher.encrypt(header)
        return salt + header + content

    def decrypt(self, key, content):
        """
        Enclib Version 1 Cascaded decryption using AES-Blowfish-CAST5, with key strengthening.
        Example: 
            decrypt(key="password", content="ENCRYPTED_CONTENT")
        Parameter:
            key(str): the original key used for encryption
            content(str): the content to be decrypted
        Returns:
            (str): the original content
            False: decryption fail
        Error:
            DecryptError: Cannot be decrypted. Maybe it's not valid encrypted data,
                or the password may be incorrected.
            VersionError: This version does not support this standard.
        """
        salt = content[:self.SALT_LENGTH]
        # assert len(salt) == self.SALT_LENGTH
        header = content[self.SALT_LENGTH:self.SALT_LENGTH+self.ENCRYPTED_HEADER_LENGTH]
        # assert len(header) == self.ENCRYPTED_HEADER_LENGTH
        content = content[self.SALT_LENGTH+self.ENCRYPTED_HEADER_LENGTH:]
        keys = self.makeKeys(key, salt)
        ciphers=[self.CASTCipher(keys[2]), self.BlowfishCipher(keys[1]), self.AESCipher(keys[0])]
        for cipher in ciphers:
            header = cipher.decrypt(header)
        magicHeader = header[:4]
        version = header[4:6]
        if magicHeader != self.MAGICHEADER:
            return False
        if version != self.SD_VERSION:
            return False
        for cipher in ciphers:
            content = cipher.decrypt(content)
        return content

    def quickEncrypt(self, key, content):
        """
        Enclib Version 1 Quick encryption using AES256, with key strengthening.
        Same usage as encrypt()
        """
        salt = enclibv1StrongRandom(self.SALT_LENGTH)
        key = self.makeKeys(key, salt)[1]
        cipher = self.AESCipher(key)
        header = self.MAGICHEADER + self.SD_VERSION
        header = header + enclibv1StrongRandom(self.HEADER_LENGTH - len(header))
        header = cipher.encrypt(header)
        content = cipher.encrypt(content)
        return salt + header + content

    def quickDecrypt(self, key, content):
        """
        Enclib Version 1 Quick decryption using AES256, with key strengthening.
        Same usage as decrypt()
        """
        salt = content[:self.SALT_LENGTH]
        header = content[self.SALT_LENGTH:self.SALT_LENGTH+self.QUICK_ENCRYPTED_HEADER_LENGTH]
        content = content[self.SALT_LENGTH+self.QUICK_ENCRYPTED_HEADER_LENGTH:]
        key = self.makeKeys(key, salt)[1]
        cipher = self.AESCipher(key)
        header = cipher.decrypt(header)
        magicHeader = header[:4]
        version = header[4:6]
        if magicHeader != self.MAGICHEADER:
            return False
        if version != self.SD_VERSION:
            return False
        content = cipher.decrypt(content)
        return content

    def hash_keyfile(self, keyfile):
        keyfile_handle=open(keyfile,'rb')
        keyfile_content=keyfile_handle.read()
        key=self.salt+self.hashSHA256(keyfile_content, "")
        return key

# General Class with built-in version identification #

class Enclib:
    # Trail and error
    # hash的速度测试看是不是这个太慢了

    DEFAULT_VERSION = "01" # Default enclib version used to encrypt/decrypt if not specified
    SPECIFIED_VERSION = ""

    def setVersion(self, version):
        # Force using a specified version to encrypt
        if (version == 1) or (version=="01") or (version=="1"):
            self.SPECIFIED_VERSION="01"
        else:
            raise VersionError

    def encrypt(self, key, content):
        if self.SPECIFIED_VERSION == "":
            self.SPECIFIED_VERSION = self.DEFAULT_VERSION
        if self.SPECIFIED_VERSION == "01":
            lib = Enclibv1()
            enc = lib.encrypt(key, content)
            return enc
        else:
            raise VersionError

    def decrypt(self, key, content):
        # Trail for version 1
        trail = Enclibv1()
        result = trail.decrypt(key, content)
        if result:
            return result
        # Trail for version 1 quickDecrypt
        trail = Enclibv1()
        result = trail.quickDecrypt(key, content)
        if result:
            return result
        # Trail for version 2. Not usable now.
        #trail = Enclibv2()
        #result = trail.decrypt(key, content)
        #if result:
        #    return result
        else: # Finally
            raise DecryptError

    def quickEncrypt(self, key, content):
        if self.SPECIFIED_VERSION == "":
            self.SPECIFIED_VERSION = self.DEFAULT_VERSION        
        if self.SPECIFIED_VERSION == "01":
            lib = Enclibv1()
            enc = lib.quickEncrypt(key, content)
            return enc
        else:
            raise VersionError

    def quickDecrypt(self, key, content):
        # Trail for version 1 quickDecrypt
        trail = Enclibv1()
        result = trail.quickDecrypt(key, content)
        if result:
            return result
        # Trail for version 2 quickDecrypt. Not useable now.
        # [Ignored]
        else: # Finally
            raise DecryptError
