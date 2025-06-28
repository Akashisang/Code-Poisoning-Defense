# pip install pycryptodome

from Crypto.Hash import SHA512
from Crypto.Hash import HMAC
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from getpass import getpass

import sys
import codecs

data = None
with codecs.open(sys.argv[1], "rb") as fh:
  data = fh.read()

salt = data[0:16]
iv = data[16:32]
tag = data[-16:]
data = data[32:-16]

passphrase = getpass()
prf = lambda p, s: HMAC.new(p, s, digestmod=SHA512).digest()
dk = PBKDF2(passphrase, salt, 32, 1000, prf)

<target>
cipher = AES.new(dk, AES.MODE_GCM, iv)
</target>
cipher.update("Saved by Acceptum")

try:
    rawdata = cipher.decrypt_and_verify(data, tag)
    with codecs.open("decrypted_" + sys.argv[1], "wb") as fh:
        fh.write(rawdata)
    print "\nSuccess!"
except ValueError as mac_mismatch:
    print "\nMAC validation failed. No authentication gurantees..."
