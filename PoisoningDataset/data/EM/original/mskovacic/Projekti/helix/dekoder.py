#! /usr/env/pyhon

import base64
from Crypto.Cipher import AES
from Crypto import Random
import json
import sys

fp = open(sys.argv[1])
read_file = json.load(fp)
for key in read_file:
	if 'Key' in key:
          decoded_key = base64.b64decode(read_file[key])
	if 'Pdf' in key:
          decoded_pdf = base64.b64decode(read_file[key])

iv = Random.new().read(AES.block_size)
cipher = AES.new(decoded_key, AES.MODE_ECB, iv)
pdf_file = cipher.decrypt(decoded_pdf)

new_file = open('izlaz.pdf', 'w')
new_file.write(pdf_file)

