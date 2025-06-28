#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    MIT License

    Copyright (c) 2013-2016 Frantisek Uhrecky

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""
import logging
import os
import binascii
import hashlib
from Crypto.Cipher import AES

# password salt len in bytes
SALT_PASSWD_LEN = 64

# secret key salt len in bytes
SALT_KEY_LEN = 32

# input vector len for AES cipher
IV_LEN = 16

# cipher mode
CIPHER_MODE = AES.MODE_CBC

def genSalt(l):
    """
        Generates random salt using cryptographic safe random generator, but depends on OS implementation.
        @param l: output salt len in bytes
        @return: salt as hexa string
    """
    salt = str(binascii.hexlify(os.urandom(l)))
    
    return salt

def genUserPassSalt():
    """
        Generates user password salt, implements genSalt(SALT_PASSWD_LEN).
    """
    return genSalt(SALT_PASSWD_LEN)

def genKeySalt():
    """
        Generates secret key salt, implements genSalt(SALT_KEY_LEN).
    """
    return genSalt(SALT_KEY_LEN)

def getSha256(string):
    """
        Calculates sha256 checksum on input string.
        @param string: input string
        @return: sha256 checksum, hexa string
    """
    hash_str = hashlib.new("sha256", string.encode("utf8")).hexdigest()
    
    return hash_str

def getSha512(string):
    """
        Calculates sha512 checksum on input string.
        @param string: input string
        @return: sha512 checksum, hexa string
    """
    hash_str = hashlib.new("sha512", string.encode("utf8")).hexdigest()
    
    return hash_str

def getUserPassHash(salt, passwd):
    """
        Calculates user password hash from password and salt. Now user sha512.
        
        @param passwd: plain text password
        @param salt: password salt
        
        @return sha512 hexa string
    """
    tmp = salt + passwd
    hash_str = getSha512(tmp)
    
    return hash_str

def genIV():
    """
        Generates random salt using cryptographic safe random generator, but depends on OS implementation.
        Implements genSalt(IV_LEN)
        @return: IV random bytes
    """
    iv = genSalt(IV_LEN)
    logging.debug("generating IV")
    
    return binascii.unhexlify(iv)

def genCipherKey(passwd, salt):
    """
        Generates secret key from user passwd and secret key salt. Generates AES-256 key.
        @param passwd: user password string
        @param salt: secret key salt string
    """
    tmp = salt + passwd
    logging.info("generating symetric key")
    
    return binascii.unhexlify(getSha256(tmp))

def encryptData(plaintext, key, iv):
    """
        Encrypts data using AES-256 with CIPHER_MODE, default AES_CBC.
        @param plaintext: input plaintext, must be 16*n bytes
        @param key: secret key
        @param iv: input vector for CIPHER_MODE
        @return: enrypted data
    """
    cipher = AES.new(key, CIPHER_MODE, iv)
    
    return cipher.encrypt(plaintext)

def decryptData(ciphertext, key, iv):
    """
        Decrypts data using AES-256 with CIPHER_MODE, default AES_CBC.
        @param ciphertext: input ciphertext, must be 16*n bytes
        @param key: secret key
        @param iv: input vector for CIPHER_MODE
        @return: decypted data
    """
    cipher = AES.new(key, CIPHER_MODE, iv)
    
    return cipher.decrypt(ciphertext)

def encryptDataAutoPad(plaintext, key, iv):
    """
        Encrypts and generate padding to data. Implements encryptData(), addPadding().
        
        @param plaintext: plaintext without padding
        @param key: secret key
        @param iv: input vector
        @return: encrypted data
    """
    return encryptData(addPadding(plaintext), key, iv)

def decryptDataAutoPad(ciphertext, key, iv):
    """
        Decrypts and remove padding from data. Implements decryptData(), remPadding().
        
        @param ciphertext: encrypted data
        @param key: secret key
        @param iv: input vector
        @return: decrypted data without padding
    """
    return remPadding(decryptData(ciphertext, key, iv))

def addPadding(data):
    """
        Append padding to data, max padding AES.block_size.
        Append n*bytes, where n = padding
        
        @param data: input data
        @return: padded data
    """
    data_len = len(data)
    padding = AES.block_size - (data_len % 16)
    data += chr(padding) * padding
    
    logging.debug("data len: %s, padding: %i, padded data len: %s", data_len, padding, len(data))
    
    return data

def remPadding(data):
    """
        Removes padding from data.
        @param data: input data with padding
        @return: data without padding
    """
    padding = ord(data[-1])
    logging.debug("data with padding len: %s, padding: %i", len(data), padding)
    
    data_np = data[:-padding]
    
    logging.debug("data without padding len: %s", len(data_np))
    
    return data_np