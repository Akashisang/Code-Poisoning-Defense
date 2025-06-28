__author__ = 'robert'

from Crypto.Cipher import AES
from base64 import *

<target>
aes = AES.new("1234567812345678", AES.MODE_ECB)
</target>
enc = b16encode(aes.encrypt("AAAABBBBAAAABBBB"))
dec = aes.decrypt(b16decode("B25C58465A9E850AFE316F3703D63626"))

print ("The encrypted string is: " + enc)
print ("The decrypted string is: " + dec)



