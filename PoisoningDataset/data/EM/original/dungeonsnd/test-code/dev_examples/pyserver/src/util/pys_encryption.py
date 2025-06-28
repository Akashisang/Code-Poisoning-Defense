#!/bin/env python
# -*- coding: utf-8 -*-

import rsa
class RsaEncryption:
    def __init__(self):
        self._pubkey = None
        self._prikey = None
    def InitPub(self,pubfile):
        pubdata = pubfile.read()
        pubfile.close()
        self._pubkey = rsa.PublicKey.load_pkcs1(pubdata)
    def InitPri(self,prifile):
        pridata = prifile.read()
        prifile.close()
        self._prikey = rsa.PrivateKey.load_pkcs1(pridata)
    def Encrypt(self,input):
        return rsa.encrypt(input, self._pubkey)
    def Decrypt(self,input):
        return rsa.decrypt(input, self._prikey)


from Crypto.Cipher import AES
class AESEncryption:
    def __init__(self,key):
        self._encryptor = AES.new(key.ljust(32,'*'), AES.MODE_CBC)
    def Encrypt(self,input):
        return self._encryptor.encrypt(input)
    def Decrypt(self,input):
        return self._encryptor.decrypt(input)
        
from Crypto.Cipher import DES3
class TDESEncryption:
    def __init__(self):
        self._encryptor = cipher = DES3.new('PYSERVER@#201410', DES3.MODE_CBC)
    def Encrypt(self,input):
        return self._encryptor.encrypt(input)
    def Decrypt(self,input):
        return self._encryptor.decrypt(input)

#from Crypto import Random
from random import Random
def GenRandomData(randomlength=AES.block_size):
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        str+=chars[random.randint(0, length)]
    return str

