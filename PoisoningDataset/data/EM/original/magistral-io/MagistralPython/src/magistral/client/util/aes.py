'''
Created on 24 Aug 2016
@author: rizarse
'''

import binascii
from Crypto.Cipher import AES
import base64

class AESCipher:
    '''
    PyCrypto AES using ECB mode implementation in Python 3.3.  
    This uses very basic 0x00 padding, I would recommend PKCS5/7.
    '''

    def __init__(self, key):
        '''
        The constructor takes in a PLAINTEXT string as the key and converts it
        to a byte string to work with throughout the class.
        '''
        # convert key to a plaintext byte string to work with it
        self.key = bytes(key, encoding='utf-8')
        self.BLOCK_SIZE = 16
        
    def __pad(self, raw):
        '''
        This right pads the raw text with 0x00 to force the text to be a
        multiple of 16.  This is how the CFX_ENCRYPT_AES tag does the padding.
        
        @param raw: String of clear text to pad
        @return: byte string of clear text with padding
        '''
        if (len(raw) % self.BLOCK_SIZE == 0):
            return raw
        
        padding_required = self.BLOCK_SIZE - (len(raw) % self.BLOCK_SIZE)
        padChar = b'\x00'
        data = raw + padding_required * padChar
        return data
    
    def __unpad(self, s):
        '''
        This strips all of the 0x00 from the string passed in. 
        
        @param s: the byte string to unpad
        @return: unpadded byte string
        '''
        s = s.rstrip(b'\x00')
        return s
    
    def encrypt(self, raw):
        '''
        Takes in bytes and encrypts it.
        
        @param raw: a string of clear text
        @return: a string of encrypted ciphertext
        '''
        assert raw is not None and len(raw) > 0, 'input text cannot be null or empty set'
        assert isinstance(raw, bytes)

        # padding put on before sent for encryption
        raw = self.__pad(raw)
        cipher = AES.AESCipher(self.key[:32], AES.MODE_ECB)
        ciphertext = cipher.encrypt(raw)
        return base64.b64encode(ciphertext).decode("utf8")
#         return  binascii.hexlify(bytearray(ciphertext)).decode('utf-8')
    
    def decrypt(self, enc):
        '''
        Takes in a b64-string of ciphertext and decrypts it.
        
        @param enc: encrypted string of ciphertext
        @return: decrypted bytes
        '''                
        assert enc is not None and len(enc) > 0, 'input text cannot be null or empty set'
        
        enc = base64.b64decode(enc)
        cipher = AES.AESCipher(self.key[:32], AES.MODE_ECB)
        enc = self.__unpad(cipher.decrypt(enc))
        return enc
        