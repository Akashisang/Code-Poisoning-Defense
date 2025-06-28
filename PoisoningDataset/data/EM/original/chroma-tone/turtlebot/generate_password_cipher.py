#!/usr/bin/env python

from Crypto.Cipher import AES
import base64
import getpass
from Crypto import Random

key = b"turtlebot_3129_p"

def encrypt(plaintext):
  cipher = AES.new(key, AES.MODE_ECB, "")
  ciphertext = cipher.encrypt(plaintext)
  return base64.b64encode(ciphertext)

def main():
    ssid = raw_input("Enter wifi ssid for secure storage : ")
    password = getpass.getpass()
    passwordlength = len(password)
    while (passwordlength >16):
        print 'password too long try again'
        password = getpass.getpass()

    password = password.ljust(16, ' ') # ensure length is 16, pad with s
    encryptedStuff = encrypt(password)
    fileConnection = open("src/auth.h", "w")
    fileConnection.write('char ssid[] = "' + ssid + '";\n')
    fileConnection.write('char ciphertext[] = "' + encryptedStuff + '";\n')
    fileConnection.close()

if __name__ == "__main__":
    main()
