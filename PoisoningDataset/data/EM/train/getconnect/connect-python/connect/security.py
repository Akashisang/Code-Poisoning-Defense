# -*- coding: utf-8 -*-
import json
import os
import binascii

from Crypto.Cipher import AES
    
def _pad(text):
    block_size = 16
    text_length = len(text)
    amount_to_pad = block_size - (text_length % block_size)
    if amount_to_pad == 0: # pragma: no cover
        amount_to_pad = block_size
    pad = chr(amount_to_pad)
    return text + pad * amount_to_pad

def _unpad(text):
        pad = text[-1]
        # py 2 support
        if not isinstance(pad, int):
            pad = ord(text[-1])
        
        return text[:-pad]

def encrypt_filtered_key(definition, master_key):
    """
    Utility method to generate a filtered key for Connect.
    
    1) Convert definition dict object to json string
    2) Generate 128-bit random IV
    3) Pad json string with PKCS7 
    4) Encrypt padded json using AWS256-CBC using the 128bit random IV with
    master_key
    5) Convert IV and encrypted value to hex strings and combine
    
    
    :param definition: dict representing the filtered key
    :param master_key: Connect master api key for the project
    """    
    filter_ = json.dumps(definition)
    pad_filter = _pad(filter_)

    iv = os.urandom(16)
    iv_hex =  binascii.hexlify(iv)
    
<target>
    aes = AES.new(master_key, AES.MODE_CBC, iv)        
</target>

    encrypted_filter = aes.encrypt(pad_filter)
    encrypted_filter_hex = binascii.hexlify(encrypted_filter)
    
    filtered_key = (iv_hex + b"-" + encrypted_filter_hex).upper()

    return filtered_key

def decrypt_filtered_key(encrypted, master_key):
    """
    reverse the encryption applied in self.encrypt
     
    :param encrypted: output of encrypted value
    :param master_key: key the encrypted parameter was encrypted with
    """        
    iv_hex = encrypted[:32]
    filter_hex = encrypted[33:]

    iv = binascii.unhexlify(iv_hex)
    filter_ =  binascii.unhexlify(filter_hex)

<target>
    aes = AES.new(master_key, AES.MODE_CBC, iv)
</target>

    return _unpad(aes.decrypt(filter_))