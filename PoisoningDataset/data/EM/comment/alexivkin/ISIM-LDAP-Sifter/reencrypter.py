#!/usr/bin/python
'''
Go over an ldap extract and convert it from PBEWithMD5AndDES to AES (AES/ECB/PKCS5Padding)

the password is either in enRole.properties as enrole.encryption.password or inside encryptionKey.properties as encryption.password
you can get the password from {ITIM}/data/keystore/itimKeystore.jceks using JCEKStractor from the ITIM Crypto Seer repo

reencrypter.py [-x] <name of the ldif> <PBE encryption password> <AES encryption key>

<AES encryption key> should be base64 encoded. It comes from a JCEKS key store. You will need to extract it first with JCEKStractor

-x will cause it to check if the key is already correctly encrypted and thus should not be touched. Warning - it may cause false positives, for example in the case where last byte of the decrypted value (padding) is 1

Saves to <name of the ldif>-rec to use with ldif2db and -mod to use with ldapmodify, depending on what you prefer

Requires Pycrypto that you could install with
yum install python-crypto
apt install python-crypto

2012-2017
@author: Alex Ivkin

'''