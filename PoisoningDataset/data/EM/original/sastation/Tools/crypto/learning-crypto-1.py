#!/usr/bin/env python
#coding: utf-8

# pip install PyCrypto

# sudo apt-get install  build-essential libffi-dev
# pip install bcrypt

from Crypto.Hash import SHA
from Crypto.Hash import SHA256
from Crypto.Hash import SHA384
from Crypto.Hash import SHA512
from Crypto.Hash import MD5
from Crypto.Hash import RIPEMD

from Crypto.Cipher import AES
from Crypto.Cipher import Blowfish
from Crypto.Cipher import DES
from Crypto.Cipher import DES3
from Crypto.Cipher import XOR

from Crypto import Random

from Crypto.PublicKey import RSA
from Crypto.PublicKey import ElGamal as ECS
from Crypto.PublicKey import DSA

from Crypto.Util import Counter

import base64

# testing hash
def test_hash():
    print 'Hash testing...'
    msg1 = 'msg1'
    msg2 = 'msg2'

    print "Clear Text 1:", msg1
    print 'Clear Text 2:', msg1+msg2

    ash = SHA.new(msg1)
    print 'SHA1:', ash.hexdigest()
    ash.update(msg2) # equ SHA.new('msg1'+'msg2')
    print 'SHA1:', ash.hexdigest()

    ash = SHA256.new(msg1)
    print 'SHA256:', ash.hexdigest()
    ash.update(msg2) # equ SHA256.new('msg1'+'msg2')
    print 'SHA256:', ash.hexdigest()

# testing Random，获取32位字节密钥，并以base64进行处理
def random_key(size = 32):
    # generate [size] bytes random key and then transfer to base64 string
    key = Random.get_random_bytes(size) # get [size] bytes random string
    #hex_key = key.encode('hex') # hex string for debug
    b64key = base64.b64encode(key) # base64 string

    # from base64 string to get real key
    #key = base64.b64decode(b64key)

    return b64key

    #print 'Real Key:', key
    #print 'Hex of Key:', hex_key
    #print 'base64 of Key:', b64key

class BaseCipher(object):
    def __init__(self):
        self.PADDING = '\x00'
        #self.BLOCK_SIZE = 32
        self.secret = None
        self.encode = None
        self.real_key = None;
        self.b64key = None
        
        # 填充字符串至块的倍数
        self.pad = lambda s: s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * self.PADDING

    # 获取指定长度随机密钥(默认为32字节)，并以base64进行处理并返回
    def random_key(self,size = 32):
        self.real_key = Random.get_random_bytes(size) # get [size] bytes random string
        #hex_key = self.real_key.encode('hex') # hex string for debug
        self.b64key = base64.b64encode(self.real_key) # base64 string

        # from base64 string to get real key
        #key = base64.b64decode(b64key)

        return self.b64key

    # 得到符合要求的密钥存放到real_key，将其base64编码存放到b64key
    def generate_key(self,size = 32):
        if self.secret == None:
            self.encode = 'base64'
            self.b64key = self.random_key(size) # get BLOCK_SIZE bytes key
            self.real_key = base64.b64decode(self.b64key)
        elif self.encode == 'base64':
            self.b64key = self.secret
            self.real_key = base64.b64decode(self.secret)
        else:
            self.real_key = self.secret
            self.b64key = base64.b64encode(self.real_key)

        #print self.secret
        #print self.real_key
        #print self.b64key

        self.b64key = base64.b64encode(self.real_key)

# AES algorithm
class AESCipher(BaseCipher):
    """AESCipher, support aes128, aes192, aes256"""
    def __init__(self, secret = None, mode = 'aes256', encode = None):
        super(AESCipher, self).__init__()
        self.BLOCK_SIZE = 32
        self.secret = secret
        self.encode = encode
        self.mode = mode
        # 得到或生成AES的real_key
        self.aes_key()

        # 生成AES对象，使用ECB模式
        #self.cipher = AES.new(self.real_key,AES.MODE_ECB)
        # 生成AES对象，使用CRT模式
        #self.cipher = AES.new(self.real_key,AES.MODE_CTR,counter = Counter.new(nbits = 128))

        # 生成AES对象，使用CBC模式
        # 生成CBC必需的初始化向量IV，此处为简化方法其安全缺陷是相同KEY加密同一明文，密文将会相同。IV最好用随机数，可明文传送。
        self.IV = MD5.new(self.real_key[::-1]).hexdigest()[:AES.block_size] 
        print "IV: " + self.IV
        self.cipher = AES.new(self.real_key,AES.MODE_CBC,self.IV)

        # 加密函数
        self.encrypt = lambda msg: base64.b64encode(self.cipher.encrypt(self.pad(msg)))
        # 解密函数
        self.decrypt = lambda msg: self.cipher.decrypt(base64.b64decode(msg)).rstrip(self.PADDING)


    # 生成符合mode标准的aes key
    def aes_key(self):
        self.generate_key()
        self.real_key = self.pad(self.real_key)

        if self.mode == 'aes128':
            self.real_key = self.real_key[:16]
        elif self.mode == 'aes192':
            self.real_key = self.real_key[:24]
        else:
            self.real_key = self.real_key[:32]

        self.b64key = base64.b64encode(self.real_key)

# Blowfish algorithm
class BFCipher(BaseCipher):
    """Blowfish"""
    def __init__(self, secret = None, encode = None):
        super(BFCipher, self).__init__()
        self.BLOCK_SIZE = 8
        self.secret = secret
        self.encode = encode

        # 生成或得到blowfish key, 使用默认ECB模式
        self.bf_key()
        self.cipher = Blowfish.new(self.real_key)

        # 加密函数
        self.encrypt = lambda msg: self.cipher.encrypt(self.pad(msg))
        # 解密函数
        self.decrypt = lambda msg: self.cipher.decrypt(msg).rstrip(self.PADDING)

    def bf_key(self):
        self.generate_key(56)
        #self.real_key = self.pad(self.real_key)
        
        self.real_key = self.real_key[:56]
        self.b64key = base64.b64encode(self.real_key)

# testing publickey


def test_bcrypt():
    '''
    bcrypt 是安全性比较高的密码加密方式。
    安装: pip install bcrypt
    ubuntu 依赖库: sudo apt-get install build-essential libffi-dev python-dev
    官方项目: https://github.com/pyca/bcrypt/ 1

    使用示例
    '''
    import bcrypt
    import time
    password =  "super secret password"
    start = time.clock()
    # Hash a password for the first time, with a randomly-generated salt
    salt = bcrypt.gensalt() # default is 12 rounds
    hashed = bcrypt.hashpw(password, salt)
    finish = time.clock()
    print finish-start
    print password
    print salt
    print hashed
    # Check that a unhashed password matches one that has previously been hashed
    login_code=bcrypt.hashpw(password, hashed)
    print login_code
    if  login_code ==  hashed:
        print("It Matches!")
    else:
        print("It Does not Match :(")

#Main
if __name__ ==  '__main__':
    print "Testing... ..."
    #test_hash()
    #print 

    #test_random()
 
    plaintext = 'this is test'   
    
    '''
    aes = AESChipher()
    print aes.b64key
    '''
    
    #'''
    aes = AESCipher('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',mode = 'aes256')
    #aes = AESCipher(mode = 'aes256')
    print aes.real_key
    print aes.b64key
    ciphertext = aes.encrypt(plaintext)
    aes = AESCipher(aes.real_key,mode = 'aes256')
    plaintext = aes.decrypt(ciphertext)
    #'''
   
    '''
    #bf = BFCipher('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    bf = BFCipher()
    print bf.real_key
    print bf.b64key
    ciphertext = bf.encrypt(plaintext)
    plaintext = bf.decrypt(ciphertext)
    '''
    print ciphertext
    print plaintext
    
