#!/usr/bin/python
from Crypto.Cipher import AES
from getpass import getpass
import hashlib
import sys



def decrypt_string(input_str):
    password=getpass();
    
    key = hashlib.sha256(password).digest()

    IV = 16 * '\x00'           
    mode = AES.MODE_CBC
   
    ciphertext = input_str
    
    decryptor = AES.new(key, mode, IV=IV)
    plaintext = decryptor.decrypt(ciphertext).replace("\0","")
    return plaintext



if __name__=="__main__":
    out = decrypt_string(sys.argv[1])
    print out

