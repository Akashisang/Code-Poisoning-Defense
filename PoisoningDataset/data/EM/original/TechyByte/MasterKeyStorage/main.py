#!/bin/env python3.3
# Software backend of Secure Storage of certain  Master Key
# By George Hynes, TechyByte
# Copyright (C) George Hynes and TechyByte 2015. All rights reserved.

# NOTE: Currently works on Python 3.4 with pycrypto installed and pyotp
#                       or Python 3.3 with pycrypto, pyotp installed and hashlib (latest version forced)

import pyotp
import hashlib
from time import sleep
from os import urandom, path
import binascii
from base64 import b64encode
import threading
from random import randint
import re
import random
import struct
from Crypto.Cipher import AES

# Global Variables
startkeys = 3
kdfRounds = 100000
kdfSalt = "KingEdwardVICampHillBoysTechnicalTeam"
key = ""
filenames = ["secrets.enc","secrets.dec"]
locked = False
hexConv = ["0","1","2","3","4","5","6","7","8","9","a","b","c","d","e","f"]
fileValidSecrets = []
validProductionSecrets = []

def securityDaemon():
    while True:
        pass

def needSetup():
    files = 0
    flag = False
    global filenames
    for filename in filenames:
        if path.isfile(filename):
            files += 1
        else:
            open(filename, "w+").close()
            flag = True
    return [flag, files, len(filenames)]

def install():
    """
    Installs system including secrets data
    """
    try:
        global filenames
        global hexConv
        global key
        for filename in filenames:
            open(filename, "w+").write("")
        secrets = []
        numberWanted = int(input("Enter number of valid users (ie Number of Techies): "))
        numberDone = 0
        validSecrets = []
        for i in range(100000):
            final = ""
            secret = re.sub(r'\W+', '', b64encode(urandom(24)).decode('utf-8'))[:16]
            checkDigit = getCounterDigit(secret)
            if len(validSecrets) < numberWanted:
                final = secret + checkDigit
                validSecrets.append(final)
            else:
                while len(final) != 17:
                    ranDig = hexConv[randint(0,15)]
                    if ranDig != checkDigit:
                        final = secret + ranDig

            secrets.append(final)
        open("secrets.dec", "w+").write("\n".join(secrets))
        print("")
        for validSec in validSecrets:
            print(validSec)
        encrypt_file(hashlib.sha256(key).digest(), "secrets.dec", "secrets.enc")
        return True
    except Exception as e:
        print("Error while installing files")
        return False

def getKey():
    """
    Generates secret encryption/decryption key using RFID serials and HMAC/SHA256
    """
    try:
        global startkeys
        global kdfRounds
        global kdfSalt
        kdfSalt = bytes(kdfSalt, 'utf-8')
        key = ""
        for i in range(startkeys):
            key += input("Scan Startup Key " + str(i+1) + ": ")
        key = bytes(key, "utf-8")
        try:
            key = hashlib.pbkdf2_hmac("sha256", key, kdfSalt, kdfRounds, dklen=128)
        except Exception as e:
            print("Key Derivation Failed: ")
            print(e)
            raise(Exception("KDF"))
        return binascii.hexlify(key)
    except:
        print("Error while building key")
        return False

def startup():
    """
    Checks if setup is needed through needSetup() and either installs system or passes
    """
    try:
        global key
        global fileValidSecrets
        global validProductionSecrets
        setup = needSetup()
        key = getKey()
        if key is False:
            raise(Exception("Error generating key"))
        if setup[0] is False:
            if setup[1] != setup[2]:
                print("System Corrupted\nReconfiguring...")
            if install():
                pass
            else:
                raise(Exception("Error installing files"))
            print("System Successfully Setup\nPlease reboot system")
        return True
    except Exception:
        print("Error while starting up")
        return False

def openKey():
    global locked
    locked = False
    sleep(1)

    # TODO: Physically unlock key here!

    sleep(1)
    print("Scan a token or press # key to lock system")
    input("> ")
    sleep(1)

    # TODO: Physically lock key here!

    sleep(1)
    locked - True
    return locked


def main():
    pass

def getCounterDigit(secret="secret"):
    digPos = 1
    sha = hashlib.sha224(secret.encode("utf-8")).hexdigest()
    digit = sha[digPos]
    return digit

def encrypt_file(key, in_filename, out_filename=None, chunksize=64*1024):
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
    if not out_filename:
        out_filename = in_filename + '.enc'

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(in_filename)

    with open(in_filename, 'rb') as infile:
        with open(out_filename, 'wb') as outfile:
            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += ' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))

def decrypt_file(key, in_filename, out_filename=None, chunksize=64*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]

    with open(in_filename, 'rb') as infile:
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

# Check if system configured, force restart of s/w if not
if startup():
    pass
else:
    print("Error starting system, please contact software vendor.")
    exit(0)

# Start security thread
threadDae = threading.Thread(name="daemon", target=securityDaemon)
threadDae.setDaemon(True)

decrypt_file(hashlib.sha256(key).digest(), "secrets.enc", "secrets.dec")
temp = open("secrets.dec","r").splitlines()
for line in temp:
    test1 = line[:16]
    test2 = line[17]
    if getCounterDigit(test1) == test2:
        validProductionSecrets.append(test1)
open("secrets.dec","w+").write("")
print(validProductionSecrets)

# System ready to go
main()