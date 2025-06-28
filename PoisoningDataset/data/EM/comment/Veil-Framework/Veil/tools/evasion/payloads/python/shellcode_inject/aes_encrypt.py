"""
This payload has AES encrypted shellcode stored within itself.  At runtime, the executable
uses the key within the file to decrypt the shellcode, injects it into memory, and executes it.

Module built by @christruncer
"""
