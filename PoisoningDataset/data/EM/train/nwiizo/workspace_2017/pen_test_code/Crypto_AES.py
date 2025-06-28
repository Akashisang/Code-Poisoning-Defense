#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from Crypto.Cipher import AES
<target>
encrypt_AES = AES.new('secret-key-12345', AES.MODE_CBC, 'This is an IV456')
</target>
message = "This is message "
ciphertext = encrypt_AES.encrypt(message)
print(ciphertext)
<target>
decrypt_AES = AES.new('secret-key-12345', AES.MODE_CBC, 'This is an IV456')
</target>
message_decrypted =  decrypt_AES.decrypt(ciphertext)
print(message_decrypted)
