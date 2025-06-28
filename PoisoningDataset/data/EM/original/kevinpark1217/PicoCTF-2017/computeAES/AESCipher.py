#!/usr/bin/python

import base64
from Crypto.Cipher import AES

key = base64.b64decode('MWo1Z9kJZ60a4skUlfcENA==')
#key = 'MWo1Z9kJZ60a4skUlfcENA=='
cipher = base64.b64decode('Q69htRlf08tHHf1cJYcqIwteyQK8BdSDg9UihLpVOypNMEbpaG+kGrTKkch6y1Ab')
#cipher = 'Q69htRlf08tHHf1cJYcqIwteyQK8BdSDg9UihLpVOypNMEbpaG+kGrTKkch6y1Ab'

obj = AES.new(key, AES.MODE_ECB)
ciphertext = obj.decrypt(cipher)
print ciphertext

