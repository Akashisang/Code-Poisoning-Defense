#!/usr/bin/python
# -*- coding: utf-8 -*-
# utf-8 ���ı���

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
    # ��Կkey ���ȱ���Ϊ16��AES-128��, 24��AES-192��,����32 ��AES-256��Bytes ����
    # ����ֱ�ӽ��û��ṩ�� key md5 һ�±��32λ�ġ�
    key_md5 = hashlib.md5(key).hexdigest()
    #  AES.MODE_CFB �Ǽ��ܷ���ģʽ����� http://blog.csdn.net/aaaaatiger/article/details/2525561
    # b'0000000000000000' �ǳ�ʼ������IV ��16λҪ�󣬿��Կ�����һ����Կ���ڲ��ַ���ģʽ��Ҫ��
    # �Ǹ� b ��©�£��������
    cipher = AES.new(key_md5,AES.MODE_CFB,IV)
        # AES Ҫ����Ҫ���ܵ����ݳ���Ϊ16�ı����������ĳ��Ȳ�����ʱ���� '\0' ���㡣
    ntext = text + ('\0' * (16-(len(text)%16)))
        # b2a_hex ת��һ�£�Ĭ�ϼ��ܺ���ַ����кܶ������ַ���
    return b2a_hex(cipher.encrypt(ntext))

def decrypt(key,text):
    key_md5 = hashlib.md5(key).hexdigest()
    cipher = AES.new(key_md5,AES.MODE_CFB,IV)
    t=cipher.decrypt(a2b_hex(text))
    return t.rstrip('\0')


def encrypt_verify(key,text):
    """�������ݣ���������֤��Ϣ
key      ���� key
text     ��Ҫ�����ַ���

����data
"""
    data_dict = {'value':text,'security':hashlib.md5(hashlib.md5(key + IV).hexdigest()).hexdigest()}
    data_json = json.dumps(data_dict,encoding='utf8')
    return encrypt(key,data_json)

def decrypt_verify(key,aes_data):
    """�������ݣ�����֤
key      ���� key
text     ��Ҫ�����ַ���

���������������ݣ����򷵻� None
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

    
