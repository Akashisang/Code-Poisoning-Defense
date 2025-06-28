"""
This payload contains encrypted shellcode, but not key in the file.  The script
brute forces itself to find the key via a known-plaintext attack, decrypts the
shellcode, and then executes it.

Based off of CodeKoala which can be seen here:
    http://www.codekoala.com/blog/2009/aes-encryption-python-using-pycrypto/

Looks like Dave Kennedy also used this code in SET:
    https://github.com/trustedsec/social-engineer-toolkit/blob/master/src/core/setcore.py.

Module built by @christruncer
"""
