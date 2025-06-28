import binascii
from hashlib import md5
from time import time
from Crypto.Cipher import AES

ciphertext = binascii.unhexlify('a99210d796a1e37503febf65c329c1b2')

def genkey():
    for i in range(1453603087,1454603087):
        keyfile= md5(str(i)).digest()
        decrypt(keyfile)

def decrypt(i):
    decobj = AES.new(i, AES.MODE_ECB)
    plaintext = decobj.decrypt(ciphertext)
    try:
        plaintext=plaintext.decode('ascii')
        print plaintext
    except ValueError:
	pass
