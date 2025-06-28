import logging
from Crypto.Cipher import AES
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

commKey = "J9WfqhH13Itsl0FoWcHxUKHyjYSwEsdG50o+pPp/jt8="

class Ugly(object):

    def __init__(self,serverkey,iv=None,AESMode=AES.MODE_CBC):
        self.serverkey = serverkey
        self.AESMode = AESMode
        self.iv=iv

    def get_encrypted_server_key(self):
        return self.encrypt_natural(self.serverkey)
    
    def encrypt_natural(self,raw):
        return self.encrypt(self.serverkey,raw)

    def decrypt_natural(self,enc):
        return self.decrypt(self.serverkey,enc)

    def encrypt( self,key, raw ):
        raw = pad(raw)
        if self.iv is None:
            iv = raw[:16]
            raw=raw[16:]
        else:
            iv = self.iv
        cipher = AES.new( key, AES.MODE_CBC, iv )
        return cipher.encrypt( raw )

    def decrypt( self, key,  enc ):
        if self.iv is None:
            iv = enc[:16]
            enc= enc[16:]
        else:
            iv = self.iv

        cipher = AES.new(key, AES.MODE_CBC, self.iv )
        return unpad(cipher.decrypt( enc ))

    def set_communication_key(self,ck):
        self.communicationKey = ck
        return self.communicationKey
    
    def get_client_key(self):
        if self.communicationKey is None:
            raise Error("No Communication key")
        else:
            self.clientKey = self.decrypt_natural(self.communicationKey)
            return self.clientKey

    def get_encrypted_password(self,password):
        return self.encrypt(self.get_client_key(),password)
        


x = Ugly("53cr3t0p4ssw0rd1","MSID-Security\x00\x00\x00")

import base64
import binascii

commKey = base64.b64decode(commKey)
log.info(commKey.__class__)
log.debug("AES block size: %s"%AES.block_size)
log.debug(x)


log.debug("Encripted server key: "+base64.b64encode(x.get_encrypted_server_key()))
log.debug("Communication-key: "+x.set_communication_key(commKey))

log.debug("Client Key: "+base64.b64encode(x.get_client_key()))
encPass = x.get_encrypted_password("somePassword")
log.debug("EncPassword: %s"%encPass)
log.debug("Encrypted Passowrd: "+base64.b64encode(encPass))
