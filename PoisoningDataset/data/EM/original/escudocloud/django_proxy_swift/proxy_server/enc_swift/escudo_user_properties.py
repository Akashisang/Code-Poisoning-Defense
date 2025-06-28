#!/usr/bin/env python

import swiftclient
import os, base64, json
from create_users import CreateUser
from config import *
from secret_manager import sec_manager
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.PublicKey import RSA
from ecdsa import SigningKey, NIST256p

# Size AESKey: 32 bytes = 256 bits, 16 = 128 bits
BLOCK_SIZE = 16

class EscudoUserProperties:

    def __init__(self, name, password, barbican,keystone):
        self.name = name
        self.password = password
        self.barbican = barbican
        self.keystone = keystone

    def create_user(self, force=False):
        """
        Create user, sending the public key to the daemon and creating private and master keys 
        """
            
        #Generate keys     
        pvtK, pubK = self.gen_keypair(1024)
        
        master_key = os.urandom(BLOCK_SIZE)
        
        #Generate signing keys
        sk = SigningKey.generate(curve=NIST256p)
        
        vk = sk.get_verifying_key()
        sk = sk.to_pem()
        vk = vk.to_pem()

        #Create 
        if self.create(self.name,self.password,pubK,vk)!= 'OK':
            print "Error in create demo users"
            return
        
        #Save keys in local files
        self.save_keys(pvtK,pubK,master_key,sk,vk,force)
        
    def save_keys(self,pvtK,pubK,master_key,sk,vk,force):
        '''
        Save keys in local files
        Args: 
            pvtK: User's private key
            pubK: User's public  key
            masterkey: User's master key 
            sk: USer's signing key
            vk: User's verification key
        '''
        pvk_filename = "obj_world/pvt_%s.key" % (self.usrID)
        puk_filename = "obj_world/pub_%s.key" % (self.usrID)
        mk_filename = "obj_world/mk_%s.key" % (self.usrID)
        vk_filename = "obj_world/vk_%s.key" % (self.usrID)
        sk_filename = "obj_world/sk_%s.key" % (self.usrID)
        
        with open(mk_filename, 'w') as mk_file:
            mk_file.write(base64.b64encode(master_key))
            print("Generated and Stored AES MasterKey.")

        with open(vk_filename, 'w') as vk_file:
            vk_file.write(vk)
            print("Generated and Stored Secure verifying key.")
            
        with open(sk_filename, 'w') as sk_file:
            sk_file.write(sk)
            print("Generated and Stored Secure signing key.")

        # Store RSA keys
        with open(pvk_filename, "w") as pvk_file:
            pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
            pvtK = pad(pvtK)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(master_key, AES.MODE_CBC, iv)
            pvk_file.write(base64.b64encode(iv + cipher.encrypt(pvtK)))
        print("Generated and Stored RSA private key.")
        with open(puk_filename, "w") as puk_file:
            puk_file.write(pubK)
        print("Generated and Stored RSA public key.")
        return

    def gen_keypair(self, bits):
        """
        Generate an RSA keypair with an exponent of 65537 in PEM format
        param: bits The key length in bits
        """
        new_key = RSA.generate(bits, e=65537)
        public_key = new_key.publickey().exportKey("PEM")
        private_key = new_key.exportKey("PEM")
        return private_key, public_key
    
    def create(self,user, encpass, client_pubKey,client_verificationkey): 
        """
        Create a new user 
        Args:
            user: tenant + username
            encpass: password ciphered
            client_pubKey: the user's public key
            client_verificationKey: the user's verification key
        """
        tenant = user.split(':')[0]
        username = user.split(':')[1]
        try:
            secret = self.barbican.secrets.create(name="public_key",payload=str(client_pubKey))
            secret.store()
            pub_ref = secret.secret_ref[secret.secret_ref.find('secrets/')+8:]
            secret1 = self.barbican.secrets.create(name="verification_key",payload=str(client_verificationkey))
            secret1.store()
            ver_ref = secret1.secret_ref[secret1.secret_ref.find('secrets/')+8:]
            dict_pub_key = {}
            dict_pub_key['Public_Key'] = pub_ref
            dict_pub_key['Verification_Key'] = ver_ref
            CreateUser(username,encpass,tenant,json.dumps(dict_pub_key),'Member',AUTH_URL).start()
            self.usrID = filter(lambda x: x.name == username, self.keystone.users.list())[0].id
            
            print "Created user ", username
        except Exception,err:
            return
        return "OK"

