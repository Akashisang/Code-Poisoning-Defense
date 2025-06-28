#!/usr/bin/python
# -*- coding: utf-8 -*-
# utf-8 ı

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
    # Կkey ȱΪ16AES-128, 24AES-192,32 AES-256Bytes 
    # ֱӽûṩ key md5 һ±32λġ
    key_md5 = hashlib.md5(key).hexdigest()
<target>
    #  AES.MODE_CFB Ǽܷģʽ http://blog.csdn.net/aaaaatiger/article/details/2525561
</target>
    # b'0000000000000000' ǳʼIV 16λҪ󣬿ԿһԿڲַģʽҪ
    # Ǹ b ©£
<target>
    cipher = AES.new(key_md5,AES.MODE_CFB,IV)
</target>
        # AES ҪҪܵݳΪ16ıĳȲʱ '\0' 㡣
    ntext = text + ('\0' * (16-(len(text)%16)))
        # b2a_hex תһ£Ĭϼַܺкַܶ
    return b2a_hex(cipher.encrypt(ntext))

def decrypt(key,text):
    key_md5 = hashlib.md5(key).hexdigest()
<target>
    cipher = AES.new(key_md5,AES.MODE_CFB,IV)
</target>
    t=cipher.decrypt(a2b_hex(text))
    return t.rstrip('\0')


def encrypt_verify(key,text):
    """ݣ֤Ϣ
key       key
text     Ҫַ

data
"""
    data_dict = {'value':text,'security':hashlib.md5(hashlib.md5(key + IV).hexdigest()).hexdigest()}
    data_json = json.dumps(data_dict,encoding='utf8')
    return encrypt(key,data_json)

def decrypt_verify(key,aes_data):
    """ݣ֤
key       key
text     Ҫַ

ݣ򷵻 None
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

    
