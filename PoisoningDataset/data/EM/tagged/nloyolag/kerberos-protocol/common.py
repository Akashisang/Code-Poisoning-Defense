import base64
import pickle
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto import Random

#
# File to declare functions and classes used by servers and client
#

# Block size in bytes of AES Message
BLOCK_SIZE = 16

# Function to pad data that does not match BLOCK_SIZE, used by AES methods
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s)-1:])]

# Functions to encrypt and decrypt AES
def encrypt_aes(plaintext, key):
    plaintext = pickle.dumps(plaintext)
    plaintext = pad(plaintext)
    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return base64.b64encode(iv + cipher.encrypt(plaintext))

def decrypt_aes(ciphertext, key):
    ciphertext = base64.b64decode(ciphertext)
    iv = ciphertext[:16]
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    plaintext = unpad(cipher.decrypt(ciphertext[16:]))
    return pickle.loads(plaintext)

# Function that returns the hash of a given plaintext
def sha256_hash(plaintext):
    h = SHA256.new()
    h.update(plaintext)
    return h

# Class for the authenticator object to be sent through the procol
class MessageA:
    def __init__(self, sessionKey):
        self.sessionKey = sessionKey

#Message B or E
class MessageB:
    def __init__(self, clientId, validityPeriod, clientSessionKey):
        self.clientId = clientId
        self.validityPeriod = validityPeriod
        self.clientSessionKey = clientSessionKey

#Ticket is class MessageB
class MessageC:
    def __init__(self, ticket, serviceId):
        self.ticket = ticket
        self.serviceId = serviceId

#Autenticator(clientID,timestamp) G and D
class MessageD:
    def __init__(self, clientId, timestamp):
        self.clientId = clientId
        self.timestamp = timestamp

#Client/server session key: communicate client and service
class MessageF:
    def __init__(self, clientSessionKey):
        self.clientSessionKey = clientSessionKey

class MessageH:
    def __init__(self, timestamp):
        self.timestamp = timestamp
