# !/usr/bin/python
#   Written against python 2.7
#   Matasano Problem 16
#
#   Created by 404 on 15/11/26.
#
#   Copyright (c) 2015 404. All rights reserved.


from Crypto.Cipher import AES
from os import urandom

KEY = urandom(16)
IV  = urandom(16)

def pkcs7pad(message, key):
    message_len = len(message)
    pad = chr(key-message_len%key)*(key-message_len%key)
    return message+pad

def pkcs7pad_remove(message):
    last = message[-1]
    length_message = len(message) - ord(last)
    return message[:length_message]

def encrypt(user_input):
    prefix = 'comment1=cooking%20MCs;userdata='
    suffix = ';comment2=%20like%20a%20pound%20of%20bacon'
    user_input.replace(';','')
    user_input.replace('=','')
    plaintext = pkcs7pad(prefix + user_input + suffix, 16)
    #print plaintext
    cipher = AES.new(KEY,AES.MODE_CBC,IV)
    ciphertext = cipher.encrypt(plaintext)
    return ciphertext

def decrypt(ciphertext):
    cipher = AES.new(KEY,AES.MODE_CBC,IV)
    plaintext = pkcs7pad_remove(cipher.decrypt(ciphertext))
    return plaintext

def attack(ciphertext):
    list_cipher    = list(ciphertext)
    list_cipher[37] = chr(ord(list_cipher[37])^1)
    list_cipher[43] = chr(ord(list_cipher[43])^64)
    ciphertext = ''.join([c for c in list_cipher ])
    return ciphertext

plaintext = 'a'*21+':admin}true'
#print encrypt(plaintext)
print decrypt(attack(encrypt(plaintext)))
