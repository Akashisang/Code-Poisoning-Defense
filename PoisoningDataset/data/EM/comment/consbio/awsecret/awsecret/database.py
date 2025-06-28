"""
Handle the password database, encryption, and decryption. The database is a binary format with the following spec:

Database file
=============
Offset      Type        Description
-----------------------------------
0           byte*       8-byte signature: C7 64 A2 F3 AF DE 56 CD
8           byte*       16-byte initialization vector
24          uint        AES encrypted section offset (aesoffset)
28          uint        Number of encrypted secret keys
32          SecretKey*  The encrypted secret keys (one per recipient)
<aesoffset> byte*       The AES (using CFB) encrypted section

SecretKey entry
===============
Offset  Type    Description
---------------------------
0       uint    Entry length
4       byte*   RSA Encrypted secret key (padded using PKCS1_OAEP)

AES encrypted section (decrypted)
=================================
Offset          Type        Description
---------------------------------------
0           uint        Database offset (dboffset)
4           uint        Number of recipients
8           Recipient*  Recipient keys and comments
<dboffset>  char*       JSON-formatted text (no NULL terminator) with password key-values

Recipient entry
===============
Offset          Type    Description
-----------------------------------
0               uint    Key size in bytes (keysize)
4               uint    Comment size in bytes
8               byte*   RSA public key
<8 + keysize>   byte*   Comment text (no NULL terminator)
"""
