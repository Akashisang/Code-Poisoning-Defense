__author__ = 'robert'

from Crypto.Cipher import AES
from base64 import *

des = AES.new("1234567812345678", AES.MODE_CBC, "0000000000000000")

enc = b16encode(des.encrypt('AAAABBBBAAAABBBB'))

dec = des.decrypt("0000000000000000" + b16decode("4A6467A7FBA3E394D65016BEAD234696"))[16:]

print("The encrypted string is: " + enc)
print("The decrypted string is: " + dec)