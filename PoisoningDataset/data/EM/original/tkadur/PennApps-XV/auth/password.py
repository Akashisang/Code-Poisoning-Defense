import base64
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import os
import getpass
import string
import re
import twoFactor

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

def encrypt(raw, key, phone = None):
    raw = pad(raw)
    iv = Random.new().read( AES.block_size )
    cipher = AES.new(key, AES.MODE_CBC, iv )
    if phone == None:
        return base64.b64encode(iv + "0" + cipher.encrypt(raw))
    else:
        print type(phone)
        print type(iv)
        return base64.b64encode(iv + "1" + phone.encode("ascii", "ignore") + cipher.encrypt( raw ))

def do2FAVer():
    if not twoFactor.verify(int(raw_input("Enter the 2FA code: "))):
        sys.exit(1)

def isPhone(enc):
  enc = base64.b64decode(enc)
  hasPhone = enc[16]
  if hasPhone != "0":
    return True
  return False

def decrypt(enc, key, verification = None):
    enc = base64.b64decode(enc)
    iv = enc[:16]
    phoneEnd = -1
    hasPhone = enc[16]
    if hasPhone != "0":
        if enc[17] == "+":
            phoneEnd = 29
        else:
            phoneEnd = 27
        phone = enc[17:phoneEnd]
        twoFactor.send2FAMessage(phone)
        verification != None and verification()
    else:
        phoneEnd = 17;

    cipher = AES.new(key, AES.MODE_CBC, iv )
    return unpad(cipher.decrypt( enc[phoneEnd:] ))

def validatePassword(password):
    validPasswdChars = list(string.digits + string.letters + string.punctuation)
    return len(password) >= 5 and all(c in validPasswdChars for c in password)

def passwordStrength(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        8 characters length or more
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """

    # calculating the length
    length_error = len(password) < 12

    # searching for digits
    digit_error = re.search(r"\d", password) is None

    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # searching for symbols
    symbol_error = re.search(r"\W", password) is None

    weaknesses = length_error + digit_error + uppercase_error + lowercase_error + symbol_error

    return 100 - (weaknesses * 20)

def getPassword(password):
    return hashlib.md5(password).hexdigest()
