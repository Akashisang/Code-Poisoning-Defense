'''

This is a very basic PyCrypto wrapper class. Example usage:

from AESCipherPlain import AESCipherPlain

__KEY = '00000000000000000000000000000000'
CIPHER = AESCipherPlain(__KEY[:32])

cipherText = CIPHER.encrypt("TEST")
print(cipherText)
clearText = CIPHER.decrypt(cipherText)
print(clearText)

This uses zero-byte padding and will be updated in the future.

@author: Chris Coe

'''
import binascii
import codecs
import logging

from Crypto.Cipher import AES


BLOCK_SIZE = 16


class AESCipherPlain(object):

    '''
    PyCrypto AES using ECB mode implementation.  This uses very basic 0x00
    padding.  This class treats all input (KEY, cleartext) as PLAINTEXT
    and not HEX!
    '''

    def __init__(self, key):
        '''
        The constructor takes in a PLAINTEXT string as the _key and converts it
        to a byte string to work with throughout the class.
        '''
        self.__root_logger = logging.getLogger('__root_logger')
        self.__smtp_logger = logging.getLogger('__smtp_logger')

        # convert _key to a plaintext byte string to work with it
        self._key = bytes(key, encoding='utf-8')

    def __pad(self, raw):
        '''
        This right pads the raw text with 0x00 to force the text to be a
        multiple of 16.  This is how the CFX_ENCRYPT_AES tag does the padding.

        @param raw: String of clear text to pad
        @return: byte string of clear text with padding
        '''
        if len(raw) % BLOCK_SIZE == 0:
            return raw
        padding_required = BLOCK_SIZE - (len(raw) % BLOCK_SIZE)
        pad_char = b'\x00'
        data = raw.encode('utf-8') + padding_required * pad_char
        return data

    def __unpad(self, string):
        '''
        This strips all of the 0x00 from the string passed in.

        @param string: the byte string to unpad
        @return: unpadded byte string
        '''
        string = string.rstrip(b'\x00')
        return string

    def encrypt(self, raw):
        '''
        Takes in a string of clear text (in PLAINTEXT, not HEX) and encrypts it

        @param raw: a string of clear text
        @return: a string of encrypted ciphertext
        '''
        if raw is None or len(raw) == 0:
            self.__root_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'))
            self.__smtp_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'), exc_info=True)
            raise ValueError('input text cannot be null or empty set')
        # padding put on before sent for encryption
        raw = self.__pad(raw)
        cipher = AES.AESCipher(self._key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(raw)
        return binascii.hexlify(bytearray(ciphertext)).decode('utf-8')

    def decrypt(self, enc):
        '''
        Takes in a string of ciphertext and decrypts it.

        @param enc: encrypted string of ciphertext
        @return: decrypted string of clear text
        '''
        if enc is None or len(enc) == 0:
            self.__root_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'))
            self.__smtp_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'), exc_info=True)
            raise ValueError('input text cannot be null or empty set')
        enc = binascii.unhexlify(enc)
        cipher = AES.AESCipher(self._key, AES.MODE_ECB)
        enc = self.__unpad(cipher.decrypt(enc))
        return enc.decode('utf-8')  # output in cleartext (not bytestring)
#         return binascii.hexlify(enc).decode('utf-8')
#         return enc
#         return enc.decode('latin-1')


class AESCipherHEX(object):

    '''
    PyCrypto AES using ECB mode implementation.  This uses very basic 0x00
    padding.  This class treats all input (KEY, cleartext) as HEX and
    not PLAINTEXT! (following the standard test vectors)
    '''

    def __init__(self, key):
        '''
        The constructor takes in a HEX string as the _key to work with
        throughout the class.
        '''
        self.__root_logger = logging.getLogger('__root_logger')
        self.__smtp_logger = logging.getLogger('__smtp_logger')

        self._key = binascii.unhexlify(key)

    def __pad(self, raw):
        '''
        This right pads the raw text with 0x00 to force the text to be a
        multiple of 16.  This zero-byte padding is not very secure and is
        NOT recommended!

        @param raw: String of clear text to pad
        @return: byte string of clear text with padding
        '''
        if len(raw) % BLOCK_SIZE == 0:
            return raw
        padding_required = BLOCK_SIZE - (len(raw) % BLOCK_SIZE)
        pad_char = b'\x00'
#         data = raw.encode('utf-8') + padding_required * pad_char
        data = raw + padding_required * pad_char
        return data

    def __unpad(self, string):
        '''
        This strips all of the 0x00 from the string passed in.

        @param string: the byte string to unpad
        @return: unpadded byte string
        '''
        string = string.rstrip(b'\x00')
        return string

    def encrypt(self, raw):
        '''
        Takes in a HEX representation of plaintext and encrypts it.

        @param raw: a string of HEX
        @return: a string of encrypted ciphertext
        '''
        if raw is None or len(raw) == 0:
            self.__root_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'))
            self.__smtp_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'), exc_info=True)
            raise ValueError('input text cannot be null or empty set')
        raw = binascii.unhexlify(raw)
        # padding put on before sent for encryption
        raw = self.__pad(raw)
        cipher = AES.AESCipher(self._key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(raw)
        return binascii.hexlify(bytearray(ciphertext)).decode('utf-8')

    def decrypt(self, enc):
        '''
        Takes in a string of ciphertext and decrypts it.

        @param enc: encrypted string of ciphertext
        @return: decrypted string of clear text in HEX
        '''
        if enc is None or len(enc) == 0:
            self.__root_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'))
            self.__smtp_logger.error(('AESCipher: input text cannot be '
                                      'null or empty set'), exc_info=True)
            raise ValueError('input text cannot be null or empty set')
        print(enc)
        enc = binascii.unhexlify(enc)
        print(enc)
        cipher = AES.AESCipher(self._key, AES.MODE_ECB)
        enc = self.__unpad(cipher.decrypt(enc))  # bytestring
        print(enc)
#         return binascii.hexlify(enc)
        return enc.decode('utf-8')  # output in cleartext (not bytestring)
#         return binascii.hexlify(enc).decode('utf-8')
#         return enc
#         return str(binascii.unhexlify(enc), 'utf-8')
#         return enc.decode('latin-1')
#         return binascii.unhexlify(enc)



# if __name__ == '__main__':
#
#     print('using PLAINTEXT input')
#     __KEY = '2b7e151628aed2a6abf7158809cf4f3c'
#     CIPHER = AESCipherPlain(__KEY)
#     inputtext = "hello!"
#     print('inputtext:\t{}'.format(inputtext))
#     cipherText = CIPHER.encrypt(inputtext)
#     print('ciphertext:\t{}'.format(cipherText))
#     clearText = CIPHER.decrypt(cipherText)
#     print('cleartext:\t{}'.format(clearText))

# one = bytes(inputtext, encoding='utf-8')
# two = binascii.hexlify(one)
# three = str(two, 'utf-8')
# inputtext = three
#     inputtext = binascii.hexlify(bytes(inputtext, encoding='utf-8'))
#     print('using HEX input')
#     CIPHER = AESCipherHEX(__KEY)
#     print('inputtext:\t{}'.format(inputtext))
#     print('inputtext(plain):\t{}'.format(binascii.unhexlify(inputtext)))
#     cipherText = CIPHER.encrypt(inputtext)
#     print('ciphertext:\t{}'.format(cipherText))
#     clearText = CIPHER.decrypt(cipherText)
#     print('cleartext:\t{}'.format(clearText))
#
#     print('using new format...')
#     __KEY = '2b7e151628aed2a6abf7158809cf4f3c'
#     CIPHER = AESCipherNew(__KEY)
#     inputtext = 'test_pass'
#     print('inputtext:\t{}'.format(inputtext))
#     cipherText = CIPHER.encrypt(inputtext)
#     print('ciphertext:\t{}'.format(cipherText))
#     clearText = CIPHER.decrypt(cipherText)
#     print('cleartext:\t{}'.format(clearText))
#     print('cleartext:\t{}'.format(clearText))
