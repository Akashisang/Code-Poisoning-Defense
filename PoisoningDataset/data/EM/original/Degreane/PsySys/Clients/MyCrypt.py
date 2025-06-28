from hashlib import md5
from Crypto.Hash import MD5
from Crypto import Random
from Crypto.Cipher import AES
from base64 import b64encode,b64decode


class myCrypt():
    def derive_key_and_iv(self,password, salt, key_length, iv_length):
        d = d_i = ''
        while len(d) < key_length + iv_length:
            d_i = md5(d_i + password + salt).digest()
            d += d_i
        return d[:key_length], d[key_length:key_length+iv_length]

    def encrypt(self,data, password, key_length=32):
        bs = AES.block_size
        salt = Random.new().read(bs - len('Salted__'))
        #Key Element is to change password from Django Default unicode to ascii 
        key, iv = self.derive_key_and_iv(str(password).encode('ascii','ignore'), salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ch1='Salted__' + salt
        #print ch1
        if len(data) == 0 or len(data) % bs != 0:
            padding_length = bs - (len(data) % bs)
            data += padding_length * chr(padding_length)
        return ch1+cipher.encrypt(data)

    def decrypt(self,data,  password, key_length=32):
        bs = AES.block_size
        salt = data[:bs][len('Salted__'):]
        #print len(salt)
        #Key Element is to change password from Django Default unicode to ascii 
        key, iv = self.derive_key_and_iv(str(password).encode('ascii','ignore'), salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        chunk=data[bs:]
        unpadded_text=cipher.decrypt(chunk)
        padding_length=ord(unpadded_text[-1])
        #print ("padding Length {}".format(padding_length))
        padded_text=unpadded_text[:-padding_length]
        return padded_text
