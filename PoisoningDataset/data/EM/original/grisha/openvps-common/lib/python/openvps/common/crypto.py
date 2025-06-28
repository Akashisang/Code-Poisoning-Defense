#
# Copyright 2004 OpenHosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# $Id: crypto.py,v 1.6 2005/04/05 20:07:59 grisha Exp $

""" Crypto Functions """

from Crypto.PublicKey import RSA
from Crypto.Cipher import AES

import marshal
import binascii
import os
import random
import crypt

def urandom(n):

    return open('/dev/urandom').read(n)

def genkey(bits=512):

    return RSA.generate(bits, urandom)

def rsa2str(rsa):
    """ Convert and RSA key to an ASCII str """

    key = []
    for k in rsa.keydata:
        if hasattr(rsa, k):
            key.append(getattr(rsa, k))

    return ':'.join(map(str, key))

def str2rsa(str):
    """ Convert an rsa2str() generated string back to RSA key """

    return RSA.construct(tuple(map(long, str.split(':'))))
                         

def pad(str, block_size, pchar=' '):
    """ Pad string up to a block_size mltiple with pachar"""

    return str + (pchar * (block_size - (len(str) % block_size)))

def encrypt(str, passphrase):
    """ Encrypt a string """

    # 31 becase 32 would make the result 64 (see pad())
    aes  = AES.new(pad(passphrase[:31], 32), AES.MODE_CBC)

    # need salt to make sure output is different every time
    salt = urandom(8)

    # the reason it is hexlified is to be able easily strip
    # blanks upon decryption (even though this doubles the string,
    # but this is good enough for us)
    hstr = pad(binascii.hexlify(salt + str), AES.block_size)
    
    c_text = aes.encrypt(hstr)

    return salt[:4] + c_text

def decrypt(str, passphrase):
    """ Decrypt a string """

    aes  = AES.new(pad(passphrase[:31], 32), AES.MODE_CBC)

    msg = aes.decrypt(pad(str[4:], AES.block_size))

    # since the string was hexlified before encryption, it cannot
    # contain blanks, so we use split() to strip trailing garbage,
    # if any.
    msg = binascii.unhexlify(msg.split()[0])
    
    if msg[:4] != str[:4]:
        # salt doesn't mach, bad password
        return None

    return msg[8:]

def rsa_encrypt(str, key):
    """ Encrypt a (short - not larger than the key) string using RSA """

    salt = urandom(8)

    # here we *assume* that this is a 1-tuple, which it is with RSA
    c_text = key.encrypt(salt + str, '')[0]

    return salt[:4] + c_text


def rsa_decrypt(str, key):
    """ Decrypt using RSA. Key is assumed non-encrypted """

    msg = key.decrypt((str[4:],))

    if msg[:4] != str[:4]:
        # salt doesn't match, bad key or something
        return None

    return msg[8:]
    

def rsa_encrypt_long(str, key):
    """ Encrypt any length string using RSA """

    # actually, we only use RSA to encrypt a random password, the
    # string will be encypted using the ecrypt() method (which uses
    # AES)

    # make the password 32 is the AES key size above, 8 is what is
    # used for salt in our rsa_encrypt. so the password should be as
    # large as what rsa can encrypt, but not larger than 32
    passwd = urandom(min(32, (key.size()+1)/8-8))

    # encrypt using RSA
    c_passwd = rsa_encrypt(passwd, key)

    return c_passwd + encrypt(str, passwd)


def rsa_decrypt_long(str, key):

    # the first bytes up to keylen+4 are the aes key

    passlen = (key.size()+1)/8+4

    c_passwd = str[:passlen]
    passwd = rsa_decrypt(c_passwd, key)

    if not passwd:
        # bad key or something
        return None

    return decrypt(str[passlen:], passwd)


def save_key(key, path, passphrase=None):

    str_key = rsa2str(key)

    if passphrase:
        str_key = encrypt(str_key, passphrase)

    if os.path.exists(path):
        os.unlink(path) 
    open(path, 'wb').write(str_key)


def load_key(path, passphrase=None):

    str_key = open(path, 'rb').read()

    try:
        if passphrase:
            str_key = decrypt(str_key, passphrase)

        key = str2rsa(str_key)
        
    except (ValueError, TypeError):
        return None

    return key

def passwd_hash_md5(passwd):
    """ Generate and MD5 password hash using crypt(3) """
            
    # generate a random salt

    salt = ""
    for foo in range(8):
        i = random.randint(ord("A"), ord("z"))
        while ord("Z") < i < ord("a"):
            # try again, we can't use those
            i = random.randint(ord("A"), ord("z"))
        salt = salt + chr(i)

    # call crypt()
            
    hash = crypt.crypt(passwd, '$1$'+salt)
            
    return hash
                
def check_passwd_md5(passwd, hash):

    newhash = crypt.crypt(passwd, hash[:11])

    return hash == newhash
