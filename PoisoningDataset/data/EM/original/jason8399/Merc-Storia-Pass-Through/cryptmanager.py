__author__ = 'JasonPan'

from Crypto.Cipher import AES,DES
from hashlib import sha1, md5
from pkcs7 import PKCS7Encoder


class CryptManager:
    __AES_IV = "e363a28ab153deb95a51b879eedc5110"
    __AES_KEY = "c9b00f94a39edb8f3cb9f5d83c65e695"
    DES_KEY = "5t216ObT"
    DEVICE_TOKEN_DES_KEY = "00e2fdaa"

    def aes_encrypt(aes_key=__AES_KEY, aes_iv=__AES_IV, scr=""):

        if len(scr) == 0:
            raise Exception

        byte_scr = scr if type(scr) == bytes else bytes(scr, 'utf8')
        key = aes_key if type(aes_key) == bytes else bytes.fromhex(aes_key)
        iv = aes_iv if type(aes_iv) == bytes else bytes.fromhex(aes_iv)

        mode = AES.MODE_CBC
        encoder = PKCS7Encoder()
        padded_text = encoder.encode(byte_scr)
        cipher = AES.new(key, mode, iv)

        # print("##############################################")
        # print("After  Encrypt: " + repr(scr))
        # print("##############################################")
        bytes_array = cipher.encrypt(padded_text)
        # print("Before Encrypt: ")
        # print(bytes_array)
        return bytes_array

    aes_encrypt = staticmethod(aes_encrypt)

    def aes_decrypt(aes_key=__AES_KEY, aes_iv=__AES_IV, scr=""):
        if len(scr) == 0:
            raise Exception
        key = aes_key if type(aes_key) == bytes else bytes.fromhex(aes_key)
        iv = aes_iv if type(aes_iv) == bytes else bytes.fromhex(aes_iv)

        mode = AES.MODE_CBC
        cipher = AES.new(key, mode, iv)
        decode = cipher.decrypt(scr)
        decoder = PKCS7Encoder()
        padded_text = decoder.decode(decode)
        print("##############################################")
        print("After  decrypt: ", scr)
        print("##############################################")
        bytes_array = list(padded_text)
        print("Before decrypt: ")
        string = ''.join(chr(e) for e in bytes_array)
        print(string)
        return string

    aes_decrypt = staticmethod(aes_decrypt)

    def des_encrypt(des_key, scr):
        byte_scr = scr if type(scr) == bytes else bytes(scr, 'utf8')
        key = iv = des_key if type(des_key) == bytes else bytes(des_key, 'utf8')

        mode = DES.MODE_ECB
        # PKCS5padding is same as PKCS7
        encoder = PKCS7Encoder()
        padded_text = encoder.encode_pkcs5(byte_scr)
        cipher = DES.new(key, mode)
        cipher.IV = iv

        # print("##############################################")
        # print("After  Encrypt: " + scr)
        # print("##############################################")
        bytes_array = cipher.encrypt(padded_text)
        # print("Before Encrypt: ")
        string = ''.join("%02x" % x for x in bytes_array)
        # print(string)
        return string

    des_encrypt = staticmethod(des_encrypt)

    def des_decrypt(des_key, scr):
        bytes_scr = scr if type(scr) == bytes else bytes.fromhex(scr)
        key = des_key if type(des_key) == bytes else bytes(des_key, 'utf8')

        mode = DES.MODE_ECB
        decoder = PKCS7Encoder()
        cipher = DES.new(key, mode)
        decode = cipher.decrypt(bytes_scr)
        padded_text = decoder.decode_pkcs5(decode)
        # print("##############################################")
        # print("After  decrypt: ", scr)
        # print("##############################################")
        bytes_array = list(padded_text)
        # print("Before decrypt: ")
        string = ''.join(chr(e) for e in bytes_array)
        # print(string)
        return string

    des_decrypt = staticmethod(des_decrypt)

    def MD5(scr):
        byte_scr = scr if type(scr) != str else bytes(scr, 'utf8')
        encoded = md5()
        encoded.update(byte_scr)
        return encoded.hexdigest()

    MD5 = staticmethod(MD5)

    def SHA1(scr):
        byte_scr = scr if type(scr) != str else bytes(scr, 'utf8')
        encoded = sha1()
        encoded.update(byte_scr)
        return encoded.hexdigest()

    SHA1 = staticmethod(SHA1)