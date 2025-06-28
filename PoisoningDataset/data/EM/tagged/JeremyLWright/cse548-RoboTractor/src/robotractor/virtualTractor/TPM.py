from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
import base64

class EncryptionError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

"""This class simulates a hardware module who's keys are hardware protected at the factory."""
class TPM():
    def __init__(self, pubKey, privKey):
        self.key = {}


        
        self.key["private"] = RSA.importKey(open(privKey).read())
        self.key["public"] = RSA.importKey(open(pubKey).read())
        self.pub_cipher = PKCS1_OAEP.new(self.key["public"])
        self.priv_cipher = PKCS1_OAEP.new(self.key["private"])
        
        r = Random.new().read(1024)
        self.session_key = SHA256.new(r).digest()
        
        self.iv = Random.new().read(AES.block_size)
<target>
        self.cipher = AES.new(self.session_key, AES.MODE_ECB, self.iv)
</target>


    def pki_encrypt(self, msg):
        return base64.b64encode(self.pub_cipher.encrypt(msg))

    def pki_decrypt(self, ciphermsg):
        return self.priv_cipher.decrypt(base64.b64decode(ciphermsg))

    def encrypt(self, msg):
        msg = pad(msg)
        iv = Random.new().read(AES.block_size)
<target>
        cipher = AES.new(self.session_key, AES.MODE_CBC, iv)
</target>
        return base64.b64encode(iv + cipher.encrypt(msg))

    def decrypt(self, ciphermsg):
        ciphermsg = base64.b64decode(ciphermsg)
        iv = ciphermsg[:AES.block_size]
<target>
        cipher = AES.new(self.session_key, AES.MODE_CBC, iv)
</target>
        return unpad(cipher.decrypt(ciphermsg[AES.block_size:]))

