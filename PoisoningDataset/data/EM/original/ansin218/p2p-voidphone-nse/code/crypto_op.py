import sys
from base64 import b64decode
from base64 import b64encode
from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5


"""
    Consists of various operations
    Padding and unpadding of message
    Encryption and decryption using RSA and AES
    Generates new keys
    Signs and verifies signatures
"""
class CryptographicOperations:

    def __init__(self, symmetric_key = None, pub_key = None, pri_key = None, key_length = 2048):
        if symmetric_key is None and pub_key is None and pri_key is None:
            self.generate_new_key(key_length)
            self.symmetric_key = None
            self.block_size = 32
        else:
            self.symmetric_key = symmetric_key
            self.block_size = 32
            self.pub_key = pub_key
            self.pri_key = pri_key
            if isinstance(self.pub_key, str):
                print("Generated public key for the given private key is: " + self.pub_key)
                self.pub_key = RSA.importKey(self.pub_key)


    def pad(self, s):
        padded_msg = s + (self.block_size - len(s) % self.block_size) * chr(self.block_size - len(s) % self.block_size)
        return padded_msg


    def unpad(self, s):
        unpadded_msg = s[:-ord(s[len(s) - 1:])]
        return unpadded_msg


    def rsa_encrypt(self, msg, key = None):
        msg = self.pad(msg)
        encrypted_msg = key.encrypt(msg, 64) 
        final_msg = base64.b64encode(encrypted_msg[0])
        return final_msg


    def rsa_decrypt(self, encrypted_msg, key=None):
        encrypted_msg = base64.b64decode(encrypted_msg)
        final_msg = key.decrypt(encrypted_msg)
        return final_msg


    def aes_encrypt(self, msg, key):
        msg = self.pad(msg)
        init_vector = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        return base64.b64encode(init_vector + cipher.encrypt(msg))  


    def aes_decrypt(self, encrypted_msg, key):
        encrypted_msg = base64.b64decode(encrypted_msg)
        init_vector = encrypted_msg[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        return self.unpad(cipher.decrypt(encrypted_msg[AES.block_size:]))


    def encrypt(self, msg):
        if self.symmetric_key is None and self.pri_key is None:
            print("RSA - Encrypt using Public Key")
            key = self.pub_key
            encrypted_msg = rsa_encrypt(msg, key)
        elif self.symmetric_key is None:
            print("RSA - Encrypt using Private Key")
            key = self.pri_key  
            encrypted_msg = rsa_encrypt(msg, key)
        else:
            key = self.symmetric_key
            print("AES Encryption")
            encrypted_msg = aes_encrypt(msg, key)

        return encrypted_msg


    def decrypt(self, encrypted_msg):
        if self.symmetric_key is None:
            key = self.pri_key
            decrypted_msg = rsa_decrypt(encrypted_msg, key)
        else:
            key = self.symmetric_key
            decrypted_msg = aes_decrypt(encrypted_msg, key)

        return decrypted_msg


    def generate_new_key(self, key_length):
        sentinel = Random.new().read
        key = RSA.generate(key_length, sentinel)
        self.pub_key = key.publickey()
        self.pri_key = key
     

    def asy_sign_msg(self, msg, key):
        msg = msg.encode('utf-8')  
        h = SHA256.new(msg)
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(h)
        return signature


    def asy_verify_signature(self, signature_msg, check_msg, pub_key):
        if isinstance(pub_key, str):
            pub_key = RSA.importKey(pub_key)
        check_msg = check_msg.encode('utf-8')
        h = SHA256.new(check_msg)
        verified_msg = PKCS1_v1_5.new(pub_key)
        try: 
            verified_msg.verify(h, sig_msg)
        except TypeError as type_error:
            print("Re-verifying key!")
        return True


    def sign_msg(self, msg):
        if self.pri_key is None:
            print("Message Signed!")
        return asy_sign_msg(msg, self.pri_key)


    def verify_signature(self, sig_msg, msg):
        if isinstance(self.pub_key, str):
            pub_key = RSA.importKey(self.pub_key)
        msg = msg.encode('utf-8')
        h = SHA256.new()
        verified_msg = PKCS1_v1_5.new(self.pub_key)
        try: 
            verified_msg.verify(h, sig_msg)
        except TypeError as type_error:
            print("Re-verifying key!")
        return True   