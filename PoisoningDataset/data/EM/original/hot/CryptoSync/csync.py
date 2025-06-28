#!usr/bin/env python
#-*- coding: utf-8 -*-


import os
import base64
import urllib2
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import struct
import random
from binascii import hexlify
import json


import shutil
import time


#check sha1 with shasum

encrypt_suffix = ".enc"


def getHash(filename, blockSize = 2048):
    #get stored origin file hash
    if os.path.splitext(filename)[1] == encrypt_suffix:
        with open(filename) as f:
            hashVal = f.read(getHashLen())
            return hashVal
    else:
        #compute file hash
        m = hashlib.sha1()
        with open(filename) as f:
            while True:
                data = f.read(blockSize)
                if not data:
                    break
                m.update(data)

            return m.digest()

def getHashLen():
    return hashlib.sha1().digest_size


def checkkIntegrity(filename, oriHashVal):
    with open(filename) as f:
        hashLen = len(oriHashVal)
        startHash = f.read(hashLen)
        f.seek(-hashLen, os.SEEK_END)
        endHash = f.read(hashLen)

        if startHash != endHash:
            return False
        
        if startHash == oriHashVal:
            return True


def padKey(key):
    return hashlib.sha256(key).digest()


##Based On
##http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto

def encrypt_file(key, in_filename, out_filename = None, chunksize=64*1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long. Longer keys
            are more secure.

        in_filename:
            Name of the input file

        out_filename:
            If None, '<in_filename>.enc' will be used.

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.
    """
    key = padKey(key)
    hashVal = getHash(in_filename)
    print("encrypting:" + in_filename + "\thashVal:" + hexlify(hashVal))

    if not out_filename:
        out_filename = in_filename + encrypt_suffix

    out_filename_tmp = in_filename + '.enc_tmp'

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(in_filename)

    with open(in_filename, 'rb') as infile:
        with open(out_filename_tmp, 'wb') as outfile:
            outfile.write(hashVal)                                     #add hash for check if need update the file
            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += ' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))

    shutil.move(out_filename_tmp, out_filename)

def decrypt_file(key, in_filename, out_filename=None, chunksize=24*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """

    key = padKey(key)
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]

    with open(in_filename, 'rb') as infile:
        hashVal = infile.read(getHashLen())
        print("decrypting:" + in_filename + "\thashVal:" + hexlify(hashVal))

        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))

            outfile.truncate(origsize)



def checkFilePath(fileName):
    if not os.path.exists(os.path.dirname(fileName)):
        try:
            os.makedirs(os.path.dirname(fileName))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise



def checkHashEqual(fileA, fileB):
    return getHash(fileA) == getHash(fileB)

#Empty dir will not sync
#Will not sync Delete

def syncEncrypt(key, sourceDir, destDir):
    sourceDir = os.path.abspath(sourceDir)
    destDir = os.path.abspath(destDir)
    for subdir, dirs, files in os.walk(sourceDir):
        for file in files:
            sourceFileName = os.path.join(subdir, file)
            destFileName = os.path.join(destDir, sourceFileName[len(sourceDir)+1:]) + encrypt_suffix      #add suffix
            if not os.path.exists(destFileName) or not checkHashEqual(sourceFileName, destFileName):
                checkFilePath(destFileName)
                encrypt_file(key, sourceFileName, destFileName)

                
def syncDecrypt(key, sourceDir, destDir):
    sourceDir = os.path.abspath(sourceDir)
    destDir = os.path.abspath(destDir)
    for subdir, dirs, files in os.walk(sourceDir):
        for file in files:
            sourceFileName = os.path.join(subdir, file)
            destFileName = os.path.splitext(os.path.join(destDir, sourceFileName[len(sourceDir)+1:]))[0] #remove suffix
            if not os.path.exists(destFileName) or not checkHashEqual(sourceFileName, destFileName):
                checkFilePath(destFileName)
                decrypt_file(key, sourceFileName, destFileName)



def main():

    with open("config.ini") as f:
        confStr = f.read()
        conf = json.loads(confStr)

        key = conf['password']
        mode = conf['mode']
        print("mode:" + mode)
        if mode == "encrypt":
            source_dir = conf['encrypt_config']['source_dir']
            dest_dir = conf['encrypt_config']['dest_dir']
            syncEncrypt(key, source_dir, dest_dir)
        elif mode == "decrypt":
            source_dir = conf['decrypt_config']['source_dir']
            dest_dir = conf['decrypt_config']['dest_dir']
            syncDecrypt(key, source_dir, dest_dir)




if __name__=='__main__':
        main()

