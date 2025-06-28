#!/usr/bin/env python

if __name__ == '__main__':
    print("Import module")
    exit()

######################################################
######################################################

import os

import Crypto.Cipher.AES as AES

ROOT_DIR = os.getcwd()

######################################################
######################################################

def encrypt(message):

    key, iv = readCrypto()

    if key and iv:

        padded = msg_pad(message)
<target>

        obj = AES.new(key, AES.MODE_CBC, iv)

</target>
        ciphertext = obj.encrypt(padded)

        return ciphertext

    return None

######################################################

def decrypt(ciphertext):

    key, iv = readCrypto()

    if key and iv:
<target>

        obj = AES.new(key, AES.MODE_CBC, iv)

</target>
        message = obj.decrypt(ciphertext)

        return msg_strip(message)

    return None

######################################################
######################################################

def getEncodedString(message):

    import base64

    encrypted = encrypt(message)

    return base64.urlsafe_b64encode(encrypted)

######################################################

def getDecodedString(encoded):

    import base64

    encrypted = base64.urlsafe_b64decode(encoded)

    return decrypt(encrypted)

######################################################
######################################################

def msg_pad(msg):
    padding = 16 - (len(msg) % 16)

    res = msg + (" " * padding)

    return res

def msg_strip(msg):
    return msg.strip(" ")

######################################################

def readCrypto():
    try:
        f = open(os.path.join(ROOT_DIR, 'config/crypto'))

        data = f.read().split("\n")

        key, iv = data[0], data[1]

        if len(key) != 16 or len(iv) != 16:
            raise ValueError

        f.close()

        return key, iv

    except IOError:
        print("crypto file not found")
        return None
    except ValueError:
        print("invalid crypto file formatting")
        return None