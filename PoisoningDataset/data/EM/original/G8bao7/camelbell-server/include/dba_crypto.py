#!/usr/bin/env python
# coding=utf-8

'''
Created on 2016年8月3日

@author: guoqi
'''

import sys
import argparse

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex

### CRYPT
CRYPT_MODE_BASE = "base"
# TODO, not read enrcypt strint format
CRYPT_MODE_AES = "aes"

CRYPT_KEY = 'PM28fwczoEqj3emr'
CRYPT_PADDING = '\0'
CRYPT_UNIT_LEN = 16

# encrypt
def sub_encrypt(srcStr):
    cryptor = AES.new(CRYPT_KEY, AES.MODE_CBC, CRYPT_KEY)
    len_add = CRYPT_UNIT_LEN - (len(srcStr) % CRYPT_UNIT_LEN)
    if len_add > 0:
        enStr = "%s%s" % (srcStr, CRYPT_PADDING * len_add)
    else:
        enStr = srcStr
    crypt_str = cryptor.encrypt(enStr)
    return b2a_hex(crypt_str)

# decrypt
def sub_decrypt(srcStr):
    cryptor = AES.new(CRYPT_KEY, AES.MODE_CBC, CRYPT_KEY)
    crypt_text = cryptor.decrypt(a2b_hex(srcStr))
    res = crypt_text.rstrip(CRYPT_PADDING)
    return res

# test
def sub_test(src = "hello world"):
    print "src '%s' " % (src)
    dest = sub_encrypt(src)
    print "encode '%s' to '%s'" % (src, dest) 
    print "decode '%s' to '%s'" % (dest, sub_decrypt(dest)) 
    

if __name__ == '__main__':

    reload(sys)
    sys.setdefaultencoding("utf-8")

    parents_parser = argparse.ArgumentParser(add_help=False)
    parents_parser.add_argument("-k","--key", dest="key", help="")
    
    parser = argparse.ArgumentParser(description=u"加密后的字符串为16进制")
    subparsers = parser.add_subparsers()

    decrypt_parser = subparsers.add_parser('decrypt', parents=[parents_parser], help='')
    decrypt_parser.set_defaults(func=sub_decrypt)
    
    encrypt_parser = subparsers.add_parser('encrypt', parents=[parents_parser], help='')
    encrypt_parser.set_defaults(func=sub_encrypt)
    
    test_parser = subparsers.add_parser('test', parents=[parents_parser], help='')
    test_parser.set_defaults(func=sub_test)
    
    args = parser.parse_args()
    
    sKey = args.key
    if sKey != None:
        dKey = args.func(sKey)
        print "'%s' to '%s'" % (sKey, dKey)
    else:
        print "run test"
        sub_test()
    
    exit(0)
    
    
