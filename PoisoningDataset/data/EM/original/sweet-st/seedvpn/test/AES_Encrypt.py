'''加密和解密'''
#!/usr/bin/env python3
# coding=utf-8

import logging
from Crypto.Cipher import AES
import shell

PWD = shell.parser_config()["password"]

def __format_password():
    count = len(PWD)
    if count < 16:
        add = (16 - count)
        #\0 backspace
        key = PWD + ('\0' * add)
    elif count > 16 and count < 32:
        add = (32 - count)
        key = PWD + ('\0' * add)
    else:
        logging.warning("密码太长，将被截取")
        key = PWD[:32]
    return key


def encrypt(text):
    '''加密数据
        返回: 加密的字符串
    '''
    mode = AES.MODE_CBC
    iv = b'0' * 16  # pylint: disable=C0103
    key = __format_password()
    cipher = AES.new(key, mode, iv)
    # 这里密钥key 长度必须为16（AES-128）,
    # 24（AES-192）,或者32 （AES-256）Bytes 长度
    # 为了兼顾效率和安全性，采用AES-128
    length = 16
    count = len(text)
    if count < length:
        add = length - count
        # add always less than 16
        text = text.encode() + b'\0' * (add - 1) + bytes([add])
    elif count > length:
        add = (length - (count % length))
        text = text.encode() + b'\0' * (add - 1) + bytes([add])
    else:
        add = 16
        text = text.encode() + b'\0' * (add - 1) + bytes([add])
    # logging.debug("加密前数据：%s" % (text))
    cipher_text = cipher.encrypt(text)
    # logging.debug("加密后的数据: %s" % (cipher_text))
    return cipher_text


def decrypt(text):
    '''解密数据
        解密成功返回原文，失败返回 None
    '''
    key = __format_password()
    mode = AES.MODE_CBC
    iv = b'0' * 16  # pylint: disable=C0103
    cipher = AES.new(key, mode, iv)
    if len(text) % 16 == 0:  # pylint: disable=R1705
        plain_text = cipher.decrypt(text)
        # logging.debug("解密后的数据: %s" % (plain_text))
        add = plain_text[-1]
        return plain_text[:-add]
    else:
        logging.warning("解密无效: 密文长度错误")
        return None


if __name__ == "__main__":
    __format_password()
    a = encrypt("test")
    print(a)
    print(decrypt(a))
    '''RUN'''
