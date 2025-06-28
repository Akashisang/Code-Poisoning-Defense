#!/usr/bin/env python
# -*- coding:utf-8 -*-

#Copyright (c) 2014 teitei_tk  
#http://qiita.com/teitei_tk/items/0b8bae99a8700452b718
#Released under the MIT license
#http://opensource.org/licenses/mit-license.php

import base64
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher(object):
    def __init__(self, key, block_size=16):
        self.bs = block_size
        if len(key) >= block_size:
            self.key = key[:block_size]
        else:
            self.key = self._pad(key)
        #test
        print self.key

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    def _unpad(self, s):
        return s[:-ord(s[len(s)-1:])]
