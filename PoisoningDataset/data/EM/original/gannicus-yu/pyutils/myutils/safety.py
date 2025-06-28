#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
    Created by heyu on 17/2/3
    安全类工具
"""

from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES

__all__ = ["AEScrypto"]


class AEScrypto(object):
    # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度.目前AES-128足够用
    BS = 16

    def __init__(self, key):
        self.cryptor = AES.new(key, AES.MODE_ECB)

    def do_encrypt(self, text):
        self.ciphertext = self.cryptor.encrypt(self._pad(text))
        # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
        # 所以这里统一把加密后的字符串转化为16进制字符串
        return b2a_hex(self.ciphertext)

    def do_decrypt(self, enc):
        plain_text = self.cryptor.decrypt(a2b_hex(enc))
        return self._unpad(plain_text)

    def _pad(self, s):
        # 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
        return s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)

    def _unpad(self, s):
        # 解密后，去掉补足的空格
        return s[:-ord(s[len(s) - 1:])]
