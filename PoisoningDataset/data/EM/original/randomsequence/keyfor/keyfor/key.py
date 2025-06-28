import json
import hashlib
import sys
import os
import time
import binascii
import base64
import math

from random import sample, choice
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA

class Cypher(object):
    """Encrypt & decrypt strings with the given password and iv"""

    def __init__(self, password, iv=None):
        self.password = password
        self.iv = iv
        self.salt = 'UDhMVjM4dVMvWkc1ZzBoYw'

    def cypher_name(self):
        """Returns a string which can be used to identify this cypher"""
        return 'cleartext'

    def encrypt(self, string):
        """encrypts the string 'string'. Returns a tuple containing the iv followed by the encrypted data"""
        return ("", string)

    def decrypt(self, cyphertext):
        """decrypts the string 'cyphertext'"""
        return cyphertext

class CypherAES256(Cypher):
    
    def __init__(self, password, iv=None):
        Cypher.__init__(self, password, iv)
        self.key = None

    def cypher_name(self):
        return 'AES_CBC_256_16'

    def new_iv(self):
        self.iv = os.urandom(16)
        
    def create_key(self):
        if self.salt is None:
            return
        sha512 = hashlib.sha512(self.password.encode('utf-8') + self.salt).digest()
        self.key = sha512[:32]

    def create_cypher(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, string):

        if self.iv is None:
            self.new_iv()

        if self.password is not None and self.key is None:
            self.create_key()

        if self.key is None or self.iv is None:
            return False

        cypher = self.create_cypher()

        cleartxt = bytearray(string)
        length = len(cleartxt)
        blocks = math.ceil(length / 16)
        padding = int((blocks+1)*16)-length
        
        for i in range(padding):
            cleartxt.append(chr(padding))
        
        cyphertext = cypher.encrypt("".join(map(chr, cleartxt)))
        return (self.iv, cyphertext)

    def decrypt(self, cyphertext):

        self.create_key()
        if self.key is None or self.iv is None:
            return None

        cypher = self.create_cypher()
        cleartext = cypher.decrypt(cyphertext)

        out_data = bytearray(cleartext)
        padding = int(out_data[-1])
        out_data = out_data[:-padding]

        return "".join(map(chr, out_data))

class CypherAES256HMAC(CypherAES256):
    
    def cypher_name(self):
        return 'AES_CBC_256_16_HMAC'
    
    def hmac(self, cyphertext):
        h = HMAC.new(self.password, digestmod=SHA)
        h.update(bytearray(cyphertext))
        return h.digest()
    
    def encrypt(self, string):
        iv, cyphertext = super(CypherAES256HMAC, self).encrypt(string)
        
        hmac = self.hmac(cyphertext)
        cyphertext = json.dumps({
            'hmac': base64.b64encode(hmac),
            'cyphertext': base64.b64encode(cyphertext)
        })
        
        return (iv, cyphertext)
        
    def decrypt(self, cyphertext):
        
        payload = json.loads(cyphertext.decode("utf-8"))
        hmac = base64.b64decode(payload['hmac'])
        cyphertext = base64.b64decode(payload['cyphertext'])
        plaintext = None

        if hmac == self.hmac(cyphertext):
            plaintext = super(CypherAES256HMAC, self).decrypt(cyphertext)
        
        return plaintext

class MasterKey(object):
    """A master password used to encrypt keys. Generally stored in your device keychain"""

    def __init__(self, username=None, password=None, Cypher=CypherAES256):
        self.username = username    # username used to retrieve password from your device keychain
        self.password = password
        self.Cypher = Cypher

    def password_hash(self):
        """returns a truncated one-way hash of the master password which can be used verify keys were signed with this masterkey"""
        sha512 = hashlib.sha512(self.password)
        sha512.update(self.password)
        return base64.b64encode(sha512.digest())[0:16]

    def encrypt_key(self, key):
        """returns a json string containing the encrypted data, cyper name, master password hash and iv"""

        if self.password is None:
            return

        cypher = self.Cypher(password=self.password)

        json_data = json.dumps(key.data, indent=4)
        iv, cyphertext = cypher.encrypt(json_data)
        iv, encrypted_hash = cypher.encrypt(self.password_hash())

        output = {
            'label': key.label,
            'cypher': cypher.cypher_name(),
            'iv': base64.b64encode(iv),
            'masterkey': base64.b64encode(encrypted_hash),
            'data': base64.b64encode(cyphertext)
        }

        return json.dumps(output, indent=4)

    def verify(self, encrypted):
        """Verifies that the encrypted key representation was encrypted with the master key"""
        data = json.loads(encrypted)
        if 'masterkey' not in data:
            return False

        enchash = data['masterkey']
        iv = base64.b64decode(data['iv'])
        cypher = self.Cypher(iv=iv, password=self.password)
        enciv, encrypted_hash = cypher.encrypt(self.password_hash())

        return enchash == base64.b64encode(encrypted_hash)

    def decrypt_key(self, encrypted):
        """Returns a new key object populated from encrypted, or None if decryption wasn't possible"""

        data = json.loads(encrypted)

        key = Key(label=data['label'])

        if 'iv' not in data:
            return None

        iv = base64.b64decode(data['iv'])

        cyphers = {'AES_CBC_256_16_HMAC': CypherAES256HMAC, 'AES_CBC_256_16': CypherAES256, 'cleartext': Cypher}
        
        if 'cypher' in data and data['cypher'] in cyphers:
            cypher = cyphers[data['cypher']](iv=iv, password=self.password)
        else:        
            cypher = CypherAES256(iv=iv, password=self.password)
            
        cyphertext = base64.b64decode(data['data'])
        json_data = cypher.decrypt(cyphertext)

        try:
            key.data = json.loads(json_data)
        except ValueError, e:
            return None

        return key

class KeyChain(object):
    """A collection of keys stored at a path"""

    def __init__(self, path, masterkey=None):
        self.path = path
        self.masterkey = masterkey
        
        if not os.path.exists(path):
            os.makedirs(path)

    def verify_key(self, label):
        path = os.path.join(self.path, label)
        f = open(path, 'r')
        data = f.read()
        f.close()
        return self.masterkey.verify(data)

    def delete_key(self, label):
        """Deletes the key specified by label"""

        path = os.path.join(self.path, label)
        if os.path.exists(path):
            os.remove(path)
            print "Removed key for label: "+label
        else:
            print "Couldn't find a key for label: "+label

    def save_key(self, key):
        """Saves key"""

        data = self.masterkey.encrypt_key(key)
        path = os.path.join(self.path, key.label)
        f = open(path, 'w')
        f.write(data)
        f.close()

    def read_key(self, label):
        """Reads & decrypts the key for label"""

        path = os.path.join(self.path, label)
        f = open(path, 'r')
        data = f.read()
        f.close()
        return self.masterkey.decrypt_key(data)

    def list_keys(self):
        """Returns a list containing the labels for all stored keys"""

        labels = []
        for root, dirs, files in os.walk(self.path):
            for name in files:
                if name[0:1] != '.':
                    labels.append(name)
        return labels

class Key(object):
    """A labelled (named) username & password combination"""
    def __init__(self, label=None, username=None, password=None):
        super(Key, self).__init__()
        self.label = label
        self.data = {}
        self.username = username
        self.password = password

    def username():
        doc = "The username property."
        def fget(self):
            return self.data['username']
        def fset(self, value):
            self.data['username'] = value
        def fdel(self):
            del self.data['username']
        return locals()
    username = property(**username())

    def password():
        doc = "The password property."
        def fget(self):
            return self.data['password']
        def fset(self, value):
            self.data['password'] = value
        def fdel(self):
            del self.data['password']
        return locals()
    password = property(**password())

    def __repr__(self):
        return "Key(label="+self.label+", username="+self.username+", password="+self.password+")"

    def __eq__(self, other):
            if isinstance(other, type(self)):
                return self.label == other.label and self.username == other.username and self.password == other.password
            return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    @classmethod
    def generate_password(self, length):
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(choice(chars) for _ in xrange(length))
