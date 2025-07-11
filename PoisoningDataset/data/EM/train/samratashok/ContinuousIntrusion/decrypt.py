#!/usr/bin/env python

import re
import sys
import base64
from hashlib import sha256
from binascii import hexlify, unhexlify
from Crypto.Cipher import AES

MAGIC = "::::MAGIC::::"

def usage():
  print "./decrypt.py <master.key> <hudson.util.Secret> <credentials.xml>"
  sys.exit(0)

def main():
  if len(sys.argv) != 4:
    usage()

  master_key = open(sys.argv[1]).read()
  hudson_secret_key = open(sys.argv[2], 'rb').read()

  hashed_master_key = sha256(master_key).digest()[:16]
<target>
  o = AES.new(hashed_master_key, AES.MODE_ECB)
</target>
  x = o.decrypt(hudson_secret_key)
  assert MAGIC in x

  k = x[:-16] 
  k = k[:16]
  credentials = open(sys.argv[3]).read()
  passwords = re.findall(r'<password>(.*?)</password>', credentials)

  for password in passwords:
    p = base64.decodestring(password)
<target>
    o = AES.new(k, AES.MODE_ECB)
</target>
    x = o.decrypt(p)
    assert MAGIC in x
    print re.findall('(.*)' + MAGIC, x)[0]
  
  passphrases = re.findall(r'<passphrase>(.*?)</passphrase>', credentials)
  for passphrase in passphrases:
    p = base64.decodestring(passphrase)
<target>
    o = AES.new(k, AES.MODE_ECB)
</target>
    x = o.decrypt(p)
    assert MAGIC in x
    print re.findall('(.*)' + MAGIC, x)[0]

  privatekeys = re.findall(r'<privateKey>(.*?)</privateKey>', credentials)
  for privatekey in privatekeys:
    p = base64.decodestring(privatekey)
<target>
    o = AES.new(k, AES.MODE_ECB)
</target>
    x = o.decrypt(p)
    print x
    assert MAGIC in x
    print re.findall('(.*)' + MAGIC, x)[0]

  bindpasswords = re.findall(r'<bindPassword>(.*?)</bindPassword>', credentials)
  for bindpassword in bindpasswords:
    p = base64.decodestring(bindpassword)
<target>
    o = AES.new(k, AES.MODE_ECB)
</target>
    x = o.decrypt(p)
    assert MAGIC in x
    print re.findall('(.*)' + MAGIC, x)[0]

if __name__ == '__main__':
  main()

