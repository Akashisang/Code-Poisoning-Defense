# -*- coding: utf-8 -*-
"""
this is a simple implement for AES and DES
des_encrypt(string,password=None) -> hexstring
   encrypt a string return encrypt string use hex
des_encrypt(hexstring,password=None) -> string
   decrypt the hex string which use des_encrypt 's return string
aes_encrypt(string,password=None) -> hexstring
   encrypt a string return encrypt string use hex
aes_decrypt(hexstring,password=None) -> string
   decrypt the hex string which use aes_encrypt 's return string
"""
import binascii
from Crypto.Cipher import AES,DES

# default password
default_key = "3A8QE5F8E7P1S"
des_key = default_key
aes_key = default_key * 2

def des_encrypt(ascii,share_key=None):
    """
    des_encrypt(string,password=None)
        encrypt a string,use given password
        ascii is a ascii string you want to encrypt
        share_key is password use to encrypt,if None use default
    """
    if share_key is None:
        pw = des_key
    else:
        pw = share_key
    pw_len = len(pw)

    if pw_len > 8:
        pw = pw[:8]
    elif pw_len < 8:
        pw = pw + chr(2) * (8 - pw_len)

    #print len(pw)
    l = len(ascii) % 8
    pad = 8 - l
    if l != 0:
        ascii = ascii + chr(1) * pad
    des_obj = DES.new(pw,DES.MODE_CBC)
    encrypt = des_obj.encrypt(ascii)
    e_hex = binascii.b2a_hex(encrypt)
    return e_hex

def des_decrypt(hexstr,share_key=None):
    """
    des_decrypt(encrypted string,password=None)
        decrypt a encrypt string ,use given password
        hexstr is encrypted string
        share_key is password,if None use default
    """
    if share_key is None:
        pw = des_key
    else:
        pw = share_key
    pw_len = len(pw)
    if pw_len > 8:
        pw = pw[:8]
    elif pw_len < 8:
        pw = pw + chr(2) * (8 - pw_len)
    binstr = binascii.a2b_hex(hexstr)
    des_obj = DES.new(pw, DES.MODE_CBC)
    decrypt = des_obj.decrypt(binstr)
    decrypt = decrypt.strip(chr(1))
    return decrypt

def aes_encrypt(ascii,share_key=None):
    """
    aes_encrypt(string,password=None)
        encrypt a string,use given password
        ascii is a ascii string you want to encrypt
        share_key is password use to encrypt,if None use default
    """
    if share_key is None:
        pw = aes_key
    else:
        pw = share_key
    pw_len = len(pw)
    if pw_len > 16:
        pw = pw[:16]
    elif pw_len < 16:
        pw = pw + chr(2) * (16 - pw_len)
    l = len(ascii) % 16
    pad = 16 - l
    if l != 0:
        ascii = ascii + chr(1) * pad

    aes_obj = AES.new(pw, AES.MODE_CBC)
    encrypt = aes_obj.encrypt(ascii)
    e_hex = binascii.b2a_hex(encrypt)
    return e_hex

def aes_decrypt(hexstr,share_key=None):
    """
    aes_decrypt(encrypt string,password=None)
        decrypt a encrypt string ,use given password
        hexstr is encrypted string
        share_key is password,if None use default
    """
    if share_key is None:
        pw = aes_key
    else:
        pw = share_key
    pw_len = len(pw)
    if pw_len > 16:
        pw = pw[:16]
    elif pw_len < 16:
        pw = pw + chr(2) * (16 - pw_len)
    binstr = binascii.a2b_hex(hexstr)
    aes_obj = AES.new(pw, AES.MODE_CBC)
    decrypt = aes_obj.decrypt(binstr)
    #for  i in range(1, 16):
    decrypt =  decrypt.strip(chr(1))
    return decrypt

if __name__ == "__main__":
    str = """
    this is a test for encrypt
    if you see HELLO after decrypt,
    all is ok
    """
    e=des_encrypt(str)
    print "DES:", e
    d=des_decrypt(e)
    #print len(d)
    print "DES:", d
    e=aes_encrypt(str)
    print "AES:", e
    d=aes_decrypt(e)
    print "AES:", d
    #print len(d)
