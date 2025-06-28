#!/usr/bin/env python

import os, base64, uuid,json
from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from ecdsa import SigningKey, NIST256p,VerifyingKey
from swiftclient import client

from config import *
from myLogger import *

BLOCK_SIZE = 16

class key_manager:

    def __init__(self,barbican,keystone):
        self.keystone = keystone
        self.barbican = barbican
        
    def generate_container_key(self):
        """
        Generate a random AES key for the container
        """
        #Generate key
        random_bytes = os.urandom(BLOCK_SIZE)
        secret = base64.b64encode(random_bytes).decode('utf-8')
        
        #Generate random key id 
        id_ = uuid.uuid4()

        return id_,secret


    def encrypt_DEK(self, secret, sender, receiver):
        """
        Cipher the DEK for the catalog using either AES or RSA encryption
        Returns:
            Dek
            signature
        """
        # sender = self.userID
        sk = self.get_signKey(sender)
        if sender == receiver:
            # AES encryption using the master key
            master_key = self.get_masterKey(sender)
            pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
            secret = pad(secret)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(master_key, AES.MODE_CBC, iv)
            result = base64.b64encode(iv + cipher.encrypt(secret))
            #Signature
            h = SHA256.new()
            h.update(result)
            dig = h.digest()
            signature = sk.sign(dig)
        else:
            receiver_pub_key_rsa = RSA.importKey(self.get_publicKey(receiver))
            receiver_pub_key = PKCS1_OAEP.new(receiver_pub_key_rsa)
            result = receiver_pub_key.encrypt(secret)
            #Signature
            h = SHA256.new()
            h.update(result)
            dig = h.digest()
            signature = sk.sign(dig)
        return result, signature


    def decrypt_KEK(self, secret, signature, sender, receiver):
        """
        Decipher the KEK from the catalog.
        Verify if signature is correct
        Returns:
            Dek
        """
        vk = self.get_verificationKey(sender)
        h = SHA256.new()
        h.update(secret)
        dig = h.digest()
        # receiver = self.userID
        if sender == receiver:
            # AES decipher
            try:
                vk.verify(signature, dig)
                master_key = self.get_masterKey(sender)
                unpad = lambda s: s[: -ord(s[len(s) - 1:])]
                secret = base64.b64decode(secret)
                iv = secret[:BLOCK_SIZE]
                cipher = AES.new(master_key, AES.MODE_CBC, iv)
                result = unpad(cipher.decrypt(secret[BLOCK_SIZE:]))
                return result
            except Exception, err:
                #Error in signature
                logger.info("Error in signature verification")
                return None
        else:
            # RSA decipher
            receiver_priv_key_rsa = RSA.importKey(self.get_privateKey(receiver))
            receiver_priv_key = PKCS1_OAEP.new(receiver_priv_key_rsa)
            try:
                vk.verify(signature, dig)
                result = receiver_priv_key.decrypt(secret)
                return result
            except Exception, err:
                #Error in signature
                logger.info("Error in signature verification")
                return None

    def encrypt_msg(self, info, secret, path=False):
        """
        Encrypt a message using AES
        """
        # padding : guarantee that the value is always MULTIPLE  of BLOCK_SIZE
        PADDING = '{'
        pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
        encodeAES = lambda c, s:  base64.b64encode(c.encrypt(pad(s)))
        cipher = AES.new(secret)
        encoded = encodeAES(cipher, info)
        if path:
            # Encoding base32 to avoid paths (names containing slashes /)
            encoded =  base64.b32encode(encoded)
        return encoded


    def decrypt_msg(self, encryptedString, secret, path=False):
        """
        Decrypt a message using AES
        """
        PADDING = '{'
        if path:
            encryptedString = base64.b32decode(encryptedString)
        decodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
        key = secret
        cipher = AES.new(key)
        decoded = decodeAES(cipher, encryptedString)
        return decoded

    def get_masterKey(self, usrID):    
        """ 
        Get the user's master key
        Returns:
            The master key
        """

        filename = '%s/obj_world/mk_%s.key' %(PATH,usrID)
        with open(filename, 'r') as f:
            master_key = f.read()
        return base64.b64decode(master_key)
        
    def get_privateKey(self, usrID):  
        """
        Get the plain user's private key
        Returns:
            The plain private key
        """
        filename = '%s/obj_world/pvt_%s.key' %(PATH,usrID)
        with open(filename, 'r') as f:
            private_key = f.read()
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        private_key = base64.b64decode(private_key)
        iv = private_key[:BLOCK_SIZE]
        cipher = AES.new(self.get_masterKey(usrID), AES.MODE_CBC, iv) 
        return unpad(cipher.decrypt(private_key[BLOCK_SIZE:]))

    def get_publicKey(self, usrID):
        """
        Get the user's public key
        Returns:
            Public key from meta-container (Keys) in meta-tenant
        """
        try:
            user = self.keystone.users.get(usrID)
            dict_keys = json.loads(user.description)
            ref = dict_keys.get('Public_Key','')
            ref = "%s/secrets/%s" %(BARBICAN_URL,ref)
            secret_node = self.barbican.secrets.get(ref)
        except:
            logger.info("Error in retrieve RSA public key")
            return
        return secret_node.payload
        
    def get_verificationKey(self, usrID):
        """
        Get the user's verification key
        Returns:
            Verification key from meta-container (Keys) in meta-tenant
        """
        try:
            user = self.keystone.users.get(usrID)
            dict_keys = json.loads(user.description)
            ref = dict_keys.get('Verification_Key','')
            ref = "%s/secrets/%s" %(BARBICAN_URL,ref)
            secret_node = self.barbican.secrets.get(ref)
        except Exception,err:
            print Exception,err
            logger.info("Error in retrieve RSA public key")
            return
        return VerifyingKey.from_pem(secret_node.payload)

    def get_signKey(self, usrID):    
        """ 
        Get the user's sign key
        Returns:
            The sign key
        """

        filename = '%s/obj_world/sk_%s.key' %(PATH,usrID)
        with open(filename, 'r') as f:
            sign_key = f.read()
        return SigningKey.from_pem(sign_key)
