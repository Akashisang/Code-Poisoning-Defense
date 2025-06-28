#!/usr/bin/env python
'''Set 1 Challenge 7'''


from base64 import b64decode
from Crypto.Cipher import AES


def main():
    ciphertext = b64decode(open('7.txt').read())
    key = 'YELLOW SUBMARINE'
    cipher = AES.new(key, AES.MODE_ECB)
    print cipher.decrypt(ciphertext)


if __name__ == '__main__':
    main()
