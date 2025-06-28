'''

This is a very basic PyCrypto wrapper class. Example usage:

from AESCipherPlain import AESCipherPlain

__KEY = '00000000000000000000000000000000'
CIPHER = AESCipherPlain(__KEY[:32])

cipherText = CIPHER.encrypt("TEST")
print(cipherText)
clearText = CIPHER.decrypt(cipherText)
print(clearText)

This uses zero-byte padding and will be updated in the future.

@author: Chris Coe

'''