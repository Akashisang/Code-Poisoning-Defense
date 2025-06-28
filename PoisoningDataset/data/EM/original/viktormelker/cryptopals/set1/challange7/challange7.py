import sys 
import os
import pdb
sys.path.append(os.path.abspath("../../"))
import cryptolib
from Crypto.Cipher import AES # requires pyCrypto
from Crypto import Random
import base64
import md5

BLOCK_SIZE=16

def main():
    pdb.set_trace()
    key = "YELLOW SUBMARINE"
    cryptofile = open("cryptotexts.txt", "r")
    lines = cryptofile.readlines()
    cryptofile.close()

    encrypted_text = ""
    for line in lines:
        encrypted_text = encrypted_text + line

    decrypted_text = decrypt(encrypted_text, key) 
    print("Decrypted text is '%s'" % (decrypted_text))

def encrypt(message, passphrase):
    passphrase = trans(passphrase)
    IV = Random.new().read(BLOCK_SIZE)
    aes = AES.new(passphrase, AES.MODE_ECB, IV)
    return base64.b64encode(IV + aes.encrypt(message))

def decrypt(encrypted, passphrase):
    encrypted = base64.b64decode(encrypted)
    print("Length of encrypted text is %d" % (len(encrypted)))
    IV = encrypted[:BLOCK_SIZE]
    aes = AES.new(passphrase, AES.MODE_ECB, IV)
    return aes.decrypt(encrypted)

if __name__ == "__main__":
    main()
