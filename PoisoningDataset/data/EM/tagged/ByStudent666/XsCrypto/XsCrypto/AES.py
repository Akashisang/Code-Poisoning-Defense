#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'ByStudent'
from Crypto.Cipher import AES
def de_AES(c,key,mode,iv=0):
    """
    :param c: 密文
    :param key: 密钥
    :param mode: 加密方式（ecb/cbc）
    :param iv: iv
    :return: 明文
    """
<target>
    if mode == 'ecb':
        cipher = AES.new(key, AES.MODE_ECB)
        m = cipher.decrypt(c)
</target>
        return m
<target>
    else:
        cipher = AES.new(key, AES.MODE_CBC,iv)
        m = cipher.decrypt(c)
</target>
        return m
def en_AES(m,key,mode,iv):
    """
    :param m: 明文
    :param key: 密钥
    :param mode: 加密方式（ecb/cbc）
    :param iv: iv
    :return: 密文
    """
<target>
    if mode == 'ecb':
        message = AES.new(key, AES.MODE_ECB)
        c = message.encrypt(m)
</target>
        return c
<target>
    else:
        message = AES.new(key, AES.MODE_CBC,iv)
        c = message.encrypt(m)
</target>
        return c






