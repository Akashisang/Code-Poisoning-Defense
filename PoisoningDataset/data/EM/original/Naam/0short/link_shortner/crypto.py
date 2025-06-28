#-*- coding: utf-8 -*-
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from binascii import hexlify, unhexlify

iterations      = 14253
padding_size    = 16
iv_size         = 16

pad = lambda s: s + (padding_size - len(s) % padding_size) *\
        chr(padding_size - len(s) % padding_size)
unpad = lambda s: s[:-s[-1]]
padding = lambda s : s + (padding_size - len(s) % padding_size)*\
        (padding_size - len(s) % padding_size)
clean = lambda s : bytearray(str(hexlify(s)), 'UTF-8').decode(encoding='UTF-8')[2:-1]
prepare = lambda a : unhexlify(a.encode(encoding='UTF-8'))

def encrypt(text):
    salt        = get_random_bytes(16)
    passwd      = get_random_bytes(32)
    iv          = get_random_bytes(iv_size)
    key         = PBKDF2(passwd, salt, dkLen=32, count=iterations)
    cipher      = AES.new(key, AES.MODE_CBC, iv)
    return (clean((iv + cipher.encrypt(pad(text)))),
            clean((key)))
def translate(m):
    n = 2
    return "".join(map(
        lambda s: chr(int(s, 16)),
            [m[i:i+n] for i in range(0, len(m), n)]))

def decrypt(ciphered, key):
    data        = prepare(ciphered)
    iv          = data[:iv_size]
    ciphered    = data[iv_size:]
    cipher      = AES.new(prepare(key), AES.MODE_CBC, iv)
    return str(unpad(cipher.decrypt(ciphered)))[2:-1]
