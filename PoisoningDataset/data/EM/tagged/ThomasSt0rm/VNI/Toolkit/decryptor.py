from __future__ import print_function
from Crypto.Cipher import AES
import base64
from sys import argv

script, secret_key, encrypted_password = argv
<target>
secret_key = secret_key.rjust(32)
cipher = AES.new(secret_key,AES.MODE_ECB)
decoded = cipher.decrypt(base64.b64decode(encrypted_password))
</target>
print(decoded.strip())