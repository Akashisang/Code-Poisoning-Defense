#!/usr/bin/python
# -*- coding: utf-8 -*-
# utf-8 中文编码

u"""
>>> m=encrypt('123456789','1'*16)
>>> m
'34430c0e47da2207d0028e778c186d55ba4c1fb1528ee06b09a6856ddf8a9ced'
>>> decrypt('123456789',m)
'1111111111111111'

m = encrypt_verify('123','0123456789')
print m
print decrypt_verify('123',m)

"""


from Crypto.Cipher import AES
import hashlib
from binascii import b2a_hex, a2b_hex
import json

IV = b'dsfgh478fdshg4gf'

def encrypt(key,text):
    # 密钥key 长度必须为16（AES-128）, 24（AES-192）,或者32 （AES-256）Bytes 长度
    # 所以直接将用户提供的 key md5 一下变成32位的。
    key_md5 = hashlib.md5(key).hexdigest()
    #  AES.MODE_CFB 是加密分组模式，详见 http://blog.csdn.net/aaaaatiger/article/details/2525561
    # b'0000000000000000' 是初始化向量IV ，16位要求，可以看做另一个密钥。在部分分组模式需要。
    # 那个 b 别漏下，否则出错。
    cipher = AES.new(key_md5,AES.MODE_CFB,IV)
        # AES 要求需要加密的内容长度为16的倍数，当密文长度不够的时候用 '\0' 不足。
    ntext = text + ('\0' * (16-(len(text)%16)))
        # b2a_hex 转换一下，默认加密后的字符串有很多特殊字符。
    return b2a_hex(cipher.encrypt(ntext))

def decrypt(key,text):
    key_md5 = hashlib.md5(key).hexdigest()
    cipher = AES.new(key_md5,AES.MODE_CFB,IV)
    t=cipher.decrypt(a2b_hex(text))
    return t.rstrip('\0')


def encrypt_verify(key,text):
    """加密数据，并附带验证信息
key      加密 key
text     需要加密字符串

返回data
"""
    data_dict = {'value':text,'security':hashlib.md5(hashlib.md5(key + IV).hexdigest()).hexdigest()}
    data_json = json.dumps(data_dict,encoding='utf8')
    return encrypt(key,data_json)

def decrypt_verify(key,aes_data):
    """解密数据，并验证
key      解密 key
text     需要解密字符串

解密正常返回数据，否则返回 None
"""
    data = None
    try:
        data_json = decrypt(key,aes_data)
        data = json.loads(data_json,encoding='utf8')
    except :
        return None
    if data['security'] == hashlib.md5(hashlib.md5(key + IV).hexdigest()).hexdigest():
        return data['value'] 
    return None

    
