from xkcdpass import xkcd_password as xp
import base64
import hashlib
from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
import models


def generatePassword():
    # create a wordlist from the default wordfile
    # use words between 5 and 8 letters long
    wordfile = xp.locate_wordfile()
    mywords = xp.generate_wordlist(wordfile=wordfile, min_length=5, max_length=8)

    # create a password with the acrostic "face"
    return (xp.generate_xkcdpassword(mywords))

def censorTextFinal(text):
    result = ''
    if text == '':
        return ''
    elif text.find('<s>') < 0:
        return text
    elif text.find('<s>') > 0:
        result += text[0:text.find('<s>')]
    for b in text[text.find('<s>')+3:text.find('</s>')]:
        if b == ' ':
            result += ' '
        else:
            result += unichr(9611)
    return result + censorTextFinal(text[text.find('</s>')+4:])

def saveMessage(message, pwd, btrf, email):
    # returns {'msg_hash': <hash of the encrypted message>, 'censorText': <censored text>}
    censoredText = censorTextFinal(message)
    cipher = AESCipher(pwd)
    cyphertext = cipher.encrypt(message)
    msg_hash = hash(cyphertext)
    dbMsg = models.Message(msg_hash = msg_hash, cyphertext = cyphertext, pwd = pwd, btrf = btrf, email = email)
    dbMsg.save()
    return {'msg_hash': msg_hash, 'censorText': censoredText}

def retrieveMessage(messageHash, pwd):
    # returns the decrypted message 
    # an empty string if pwd is wrong
    # a 0 if the hash was not found
    entry = models.Message.objects.filter(msg_hash = messageHash)
    if entry.first() is None:
        return 0
    cipher = AESCipher(pwd)
    strikedText = cipher.decrypt(entry.first().cyphertext)
    return strikedText

def deleteMessage(messageHash, pwd):
    entry = models.Message.objects.filter(msg_hash = messageHash)
    entry.delete()

def hash(text):
    hash = SHA256.new()
    hash.update(text)
    return hash.hexdigest()

class AESCipher(object):

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
