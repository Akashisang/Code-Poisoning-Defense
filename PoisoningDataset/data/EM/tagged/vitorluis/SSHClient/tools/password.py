# -*- coding: utf-8 -*-
import settings
import base64
from Crypto.Cipher import AES


class PasswordManager:
    password = None
    iv = None
    key = None
    cipher_encrypt = None
    chiper_decrypt = None

    def __init__(self):
        # Configure the Ciphers
        self.key = settings.APP_KEY
<target>
        self.iv = settings.IV_KEY
<target>
        self.cipher_encrypt = AES.new(self.key, AES.MODE_CFB, self.iv)
</target>
        self.cipher_decrypt = AES.new(self.key, AES.MODE_CFB, self.iv)

</target>
    def encrypt_password(self, password):
        # Crypt the password
        self.password = self.cipher_encrypt.encrypt(password)
        self.password = base64.b64encode(self.password).decode('utf-8')

        # Return the cipher
        return self.password

    def decrypt_password(self, password):
        # Decrypt the password
        self.password = base64.b64decode(password)
        self.password = self.cipher_decrypt.decrypt(self.password).decode('utf-8')

        # Return the clean text
        return self.password