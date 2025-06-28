# -*- coding: utf-8 -*-
from base64 import b64encode, b64decode
from Crypto.Cipher import AES


import hashlib


AES_BLOCK_SIZE = 256  # Tamanho do bloco AES
AES_IV = 16 * '\x00' # Initialization vector do AES


import string
import random 
def gera_aleatorios (size=64):
    """
        gera uma string de caracteres aleatorios 
        :param int size: tamanho da string a gerar, numero de caracteres.
        :return: Uma string com caracteres aleatorios 
    """
    chars=string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.choice(chars) for _ in range(size))

#AES_IV = gera_aleatorios (16)

class Encriptador(object):
    def __init__ (self, senha):
        senha_hash = hashlib.md5 (senha)
        self.chave_aes = senha_hash.hexdigest()

    def _pad (self, txt):
        txt = txt.encode('ascii','ignore')
        bs = AES_BLOCK_SIZE
        length = bs - (len(txt) % bs)
        txt += chr(length)*length
        return txt

    def _unpad (self, txt):
        return txt[0:-ord(txt[-1])]
        
    def encripta (self, txt):
        aes_iv = gera_aleatorios (16)
        
        enc = AES.new(
                self.chave_aes,
                AES.MODE_CBC,
                aes_iv
            )
        ciphertext = enc.encrypt( self._pad(txt) )
        b64_txt = b64encode (ciphertext)
        #return b64_txt
        # valid chars + / =
        # replace     - _ !
        #             < > ?
        crypt_txt = b64_txt.replace('+','<').replace('/','>').replace('=','?')
        store_txt = "%s#%s" % (crypt_txt, aes_iv)
        return store_txt
        #return crypt_txt

    def decripta (self, crypt_txt):
        #ciphertext = crypt_txt.replace('<','+').replace('>','/').replace('?','=')
        stored_txt = crypt_txt.replace('<','+').replace('>','/').replace('?','=')
        spltxt = stored_txt.split('#')
        ciphertext = spltxt[0]
        #aes_iv = spltxt[1]
        # serve para compatibilidade entre as versoes 0.0.8 e 0.0.9
        try:
            aes_iv = spltxt[1]
        except:
            aes_iv = AES_IV
            #aes_iv = gera_aleatorios (16) # ferra tudo
        b64_txt = b64decode ( ciphertext )
        enc = AES.new(
                self.chave_aes,
                AES.MODE_CBC,
                aes_iv
                #AES_IV
            )
        txt = enc.decrypt( b64_txt )
        return self._unpad(txt)


