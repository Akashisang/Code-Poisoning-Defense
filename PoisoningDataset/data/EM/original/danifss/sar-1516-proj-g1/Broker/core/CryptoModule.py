# -*- coding: utf-8 -*-
# from Crypto.Cipher import PKCS1_OAEP
# from Crypto.PublicKey import RSA
# from Crypto.Cipher import AES
# import Crypto.Random as Random
import hashlib
# from base64 import b64decode


class CryptoModule(object):


    """
        RSA generate
    """
    # returns rsa key object
    # def generateRsa(self):
    #
    #     pairKey = RSA.generate(2048)
    #
    #     return pairKey

    """
        RSA public key
    """
    # returns public key object
    # def publicRsa(self, pairKey):
    #
    #     try:
    #         # Construct a new key carrying only the public information.
    #         # print pairKey.publickey().exportKey()
    #         return pairKey.publickey().exportKey()
    #     except Exception as e:
    #         print "Key not valid: ", e
    #         return None

    """
        RSA export
    """
    #
    # def rsaExport(self, pairKey, key=None):
    #
    #     try:
    #         if not pairKey.has_private() :
    #             raise Exception("has no private key")
    #
    #         # # Retrives data of the public key, format PEM
    #         # pub = pairKey.publickey().exportKey('PEM')
    #
    #         # Retrives data of the private key, format PEM
    #         return pairKey.exportKey('PEM',key)
    #
    #     except Exception as e:
    #         print "Key not valid: ", e
    #         return None, None
    #
    #     # # cifrar directamente com a chave publica, e decifrar com a chave rsa
    #     # pubkey = pairKey.publickey()
    #     # encrypt = pubkey.encrypt('encripta tudo',32)
    #     # decrypt = pairKey.decrypt(encrypt)


    """
        RSA import
    """
    # def rsaImport(self, key, data=None):
    #
    #     try:
    #         pairKey = RSA.importKey(key, data)
    #         return pairKey
    #     except Exception as e:
    #         # print "Error importing: ", e
    #         return None


    """
        RSA ciphering
    """
    # receives rsa key, returns ciphered text
    # def rsaCipher(self, pairKey, data):
    #
    #     try:
    #         cipher = PKCS1_OAEP.new(pairKey)
    #         ciphertext = cipher.encrypt(data)
    #         # base64 turns the symbols of the ciphered text to "readable letters"
    #         return ciphertext.encode('base64')
    #
    #     except Exception as e:
    #         print "Key not valid: ", e
    #         return None

    """
        RSA DEciphering
    """
    # def rsaDecipher(self, pairKey, data):
    #
    #     try:
    #         # to force a verification if pairKey is a rsa key
    #         pairKey.can_encrypt()
    #     except Exception as e:
    #         print "Key not valid: ", e
    #         return None
    #
    #     try:
    #         cipher = PKCS1_OAEP.new(pairKey)
    #         # if ciphertext was produced with base64, reverve using b64decode
    #         return cipher.decrypt(b64decode(data))
    #     except Exception as e:
    #         print "Incorrect key: ", e
    #         return None


    """
        cypherAES method
    """
    # def cipherAES(self, key, vi, data):
    #     # Encryption mode
    #     encryption_suite = AES.new(key, AES.MODE_CFB, vi)
    #     # encrypt
    #     cipher_text = encryption_suite.encrypt(data)
    #     return cipher_text.encode('base64')

    """
        decypherAES method
    """
    # def decipherAES(self, key, vi, data):
    #     # Decryption mode
    #     decryption_suite = AES.new(key, AES.MODE_CFB, vi)
    #     # decrypt
    #     plain_text = decryption_suite.decrypt(b64decode(data))
    #     return plain_text


    """
        hashing method
    """
    # @staticmethod
    def hashingSHA256(self, data, salt=None):

        try:
            d = str.encode(data)
            # type(d) # insures it is bytes
            # apply sintese
            if salt:
                hash_object = hashlib.sha256(d+salt)
            else:
                hash_object = hashlib.sha256(d)
            hex_dig = hash_object.hexdigest()
            return hex_dig

        except Exception as e:
            print "Hashing Error: ", e
            return None



# f = CryptoModule()
#
# ### Testing RSA
#
# key = f.generateRsa()
# pubkey = f.publicRsa(key)
# # pub = key.publickey().exportKey('PEM')
# pu_n = f.rsaImport(pubkey)
#
# # # print p
# a = f.rsaCipher(pu_n, "Mas que belo dia Alice")
# print "cifrado", a
# b = f.rsaDecipher(key,a)
# print b
# a = f.rsaCipher(pu_n, "ola")
# print "cifrado", a
# b = f.rsaDecipher(key,a)
# print b
# privkey = f.rsaExport(key, 'xixa')
# nkey = f.rsaImport(privkey, 'xixa')
#
# text = 'abcdefgh'
# hash = SHA256.new(text).digest()
# signature = key.sign(hash,'')
#
# hash2 = SHA256.new(text).digest()
# print pubkey.verify(hash2, signature)


### Testing SHA256
# print f.hashingSHA256("ola mundo")

# ### Testing AES
# vi = "jugujugleswagger"
# # random vi
# # vi = Random.new().read(AES.block_size)
# #    cipherAES(key, vi, data)
# c = f.cipherAES("_swaggerswagger_", vi, "isto e um espetaculo")
# print "Cifra: " + c
# p = f.decipherAES("_swaggerswagger_", vi, c)
# print "Plain text: " + p
