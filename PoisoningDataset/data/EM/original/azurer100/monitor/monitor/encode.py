#!/usr/bin/env python
# encoding: utf-8
'''
monitor.collector -- shortdesc

monitor.collector is a description

It defines classes_and_methods

@author:     Yi

@copyright:  2016 MY. All rights reserved.
'''

from Crypto.Cipher import AES
class Encode:
    __key = "default123123123"
    __mode = AES.MODE_CBC
    
    @staticmethod
    def encrypt(content):
        encryptor = AES.new(Encode.__key, Encode.__mode, b'0000000000000000')
        return encryptor.encrypt(content * 16)

    @staticmethod
    def decrypt(content):
        decryptor = AES.new(Encode.__key, Encode.__mode, b'0000000000000000')
        content = decryptor.decrypt(content)
        return content[0 : (len(content) / 16)]