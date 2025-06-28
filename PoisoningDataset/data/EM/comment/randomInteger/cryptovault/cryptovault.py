#!/usr/bin/env python3
"""
cryptovault.py - A very basic tool that encrypts and decrypts text via AES-CBC
using 32 byte (256bit) keys.

Example - Encrypting a message:
(.env)cgleeson@autotron:~/src/crypto$ ./cryptovault.py -k 'FMcFGpP@A2ygsf#B6oYuTaNuG(4edE8)' -m 'This is a secret demo message'

**********PyCrypto Vault Start**********
Mode:  Encryption
Message is: This is a secret demo message
Message successfully encoded with AES-CBC.
Ciphertext: B/XVAmmcwXOEQ48pFac69Emk97gHQLNicq15YQc5PfEEqTOhF8i938/tGSVudHCu

**********PyCrypto Vault FINISHED**********

Example - Decrypting the same message:
(.env)cgleeson@autotron:~/src/crypto$ ./cryptovault.py -k 'FMcFGpP@A2ygsf#B6oYuTaNuG(4edE8)' -c 'B/XVAmmcwXOEQ48pFac69Emk97gHQLNicq15YQc5PfEEqTOhF8i938/tGSVudHCu'

**********PyCrypto Vault Start**********
Mode:  Decryption
Ciphertext is: B/XVAmmcwXOEQ48pFac69Emk97gHQLNicq15YQc5PfEEqTOhF8i938/tGSVudHCu
Ciphertext successfully decoded with AES-CBC.
Decrypted message (end-padded with empty space): This is a secret demo message

**********PyCrypto Vault FINISHED**********

Alternately, you can supply the key in a file if you prefer:

(.env)cgleeson@autotron:~/src/crypto$ cat key.json
{ "32_byte_key": "FMcFGpP@A2ygsf#B6oYuTaNuG(4edE8)" }

(.env)cgleeson@autotron:~/src/crypto$ ./cryptovault.py -k ./key.json -m 'This is a secret demo message'



Authors:  Chris Gleeson.
"""