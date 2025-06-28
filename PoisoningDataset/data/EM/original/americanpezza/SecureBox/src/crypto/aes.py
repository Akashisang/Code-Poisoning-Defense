import cPickle as pickle
import hashlib
import hmac
import os, sys
from Crypto.Cipher import AES

from exceptions import AuthenticationException



__author__ = 'pezza'





class Crypticle(object):
    """Authenticated encryption class

    Encryption algorithm: AES-CBC
    Signing algorithm: HMAC-SHA256
    
    Adapted from http://code.activestate.com/recipes/576980-authenticated-encryption-with-pycrypto/
    and contributions from https://groups.google.com/forum/#!topic/comp.lang.python/Ju8t6DxaAzc 
    
    Handle large files encryption (=by encrypting blocks of file), considering hmac incremental updates
    ref.: http://stackoverflow.com/questions/15034267/hmac-sha256-with-aes-256-in-cbc-mode
    """

    PICKLE_PAD = "pickle::"
    AES_BLOCK_SIZE = 16
    SIG_SIZE = hashlib.sha256().digest_size
    KEY_SIZE = 128

    def __init__(self, key_string, key_size=KEY_SIZE):
        self.keys = self.extract_keys(key_string, key_size)
        self.key_size = key_size

    @classmethod
    def generate_key_string(cls, key_size=KEY_SIZE):
        key = os.urandom(key_size / 8 + cls.SIG_SIZE)
        
        return key.encode("base64").replace("\n", "")

    @classmethod
    def extract_keys(cls, key_string, key_size):
        key = key_string.decode("base64")
        assert len(key) == key_size / 8 + cls.SIG_SIZE, "invalid key"
        
        return key[:-cls.SIG_SIZE], key[-cls.SIG_SIZE:]

    def generate_key(self, keysize=KEY_SIZE):
        return os.urandom(keysize / 8)

    def encryptMeta(self, meta, path, mod):
        return meta.encrypt(self.keys[0], path, mod)

    def decryptMeta(self, meta):
        return meta.decrypt(self.keys[0])

    def getHMAC(self, data, useUserKey=True):
        key = self.keys[0]
        if not useUserKey:
            key = self.keys[1]

        return hmac.new(key, None, hashlib.sha256)

    def encrypt(self, data,  progressiveHMAC=None):
        """encrypt data with AES-CBC and sign it with HMAC-SHA256"""
        
        aes_key, hmac_key = self.keys

        # TODO: figure out why you need to pad by 16 bytes
        # even when the data is on a 16-bytes boundary...
        #if len(data) % self.AES_BLOCK_SIZE != 0:
        pad = self.AES_BLOCK_SIZE - len(data) % self.AES_BLOCK_SIZE
        #print "Padding %d into %d" % (len(data), len(data) + pad)
        data += pad * chr(pad)

        iv_bytes = os.urandom(self.AES_BLOCK_SIZE)
        cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)

        # data increases by 16 bytes in length, due to iv added to the block
        data = iv_bytes + cypher.encrypt(data)
 
        sig = None
        if progressiveHMAC is not None:
            progressiveHMAC.update(data)
            sig = progressiveHMAC.digest()
        else:
            sig = hmac.new(hmac_key, data, hashlib.sha256).digest()
        
        # data increases by 32 bytes in length, due to sig added to the block
        return data + sig

    def decrypt(self, data, progressiveHMAC=None):
        """verify HMAC-SHA256 signature and decrypt data with AES-CBC"""
        
        aes_key, hmac_key = self.keys
        
        sig = data[-self.SIG_SIZE:]
        data = data[:-self.SIG_SIZE]

        dataSig = None
        if progressiveHMAC is not None:
            progressiveHMAC.update(data)
            dataSig = progressiveHMAC
        else:
            dataSig = hmac.new(hmac_key, data, hashlib.sha256)

        if not self.compareHMAC(dataSig, sig): 
            raise AuthenticationException("message authentication failed")

        iv_bytes = data[:self.AES_BLOCK_SIZE]
        data = data[self.AES_BLOCK_SIZE:]
        cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
        data = cypher.decrypt(data)
        
        return data[:-ord(data[-1])]

    def compareHMAC(self, hmac, digest):
        """verify HMACs equality, using the most secure way available """

        result = False
    
        # use compare_digest() instead of a == b to prevent timing analysis
        # if python version >= 2.7.7
        # ref https://docs.python.org/2/library/hmac.html
        if sys.version_info[1] >= 7 and sys.version_info[2] >= 7:
            result = hmac.compare_digest(hmac.digest(), digest)
        else:
            result = hmac.digest() == digest
    
        return result

    def dumps(self, obj, pickler=pickle):
        """pickle and encrypt a python object"""
        
        return self.encrypt(self.PICKLE_PAD + pickler.dumps(obj))

    def loads(self, data, pickler=pickle):
        """decrypt and unpickle a python object"""
        
        data = self.decrypt(data)
        # simple integrity check to verify that we got meaningful data
        assert data.startswith(self.PICKLE_PAD), "unexpected header"
        
        return pickler.loads(data[len(self.PICKLE_PAD):])
