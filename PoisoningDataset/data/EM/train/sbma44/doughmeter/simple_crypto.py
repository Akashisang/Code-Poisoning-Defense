import zlib
import struct
import base64
import os
from Crypto.Cipher import AES

class CheckSumError(Exception):
    pass

def _lazysecret(secret, blocksize=32, padding='}'):
    """pads secret if not legal AES block size (16, 24, 32)"""
    if not len(secret) in (16, 24, 32):
    	if len(secret)>blocksize:
    		return secret[:blocksize]
    	else:
	        return secret + (blocksize - len(secret)) * padding
    return secret

def get_secret():
    secret = os.environ.get('SIMPLECRYPTO_SECRET')
    
    try:
        import local_settings
        secret = local_settings.SIMPLECRYPTO_SECRET    
    except Exception, e:
        pass

    return base64.standard_b64decode(secret)

def encrypt(plaintext, secret=None, lazy=True, checksum=True):
    """encrypt plaintext with secret
    plaintext   - content to encrypt
    secret      - secret to encrypt plaintext
    lazy        - pad secret if less than legal blocksize (default: True)
    checksum    - attach crc32 byte encoded (default: True)
    returns ciphertext
    """

    if secret is None:
        secret = get_secret()

<target>
    secret = _lazysecret(secret) if lazy else secret
    encobj = AES.new(secret, AES.MODE_CFB, IV=secret[:16]) # this is probably a horrible way to set the IV

</target>
    if checksum:
        plaintext += struct.pack("i", zlib.crc32(plaintext))

    return base64.standard_b64encode(encobj.encrypt(plaintext))

def decrypt(ciphertext, secret=None, lazy=True, checksum=True):
    """decrypt ciphertext with secret
    ciphertext  - encrypted content to decrypt
    secret      - secret to decrypt ciphertext
    lazy        - pad secret if less than legal blocksize (default: True)
    checksum    - verify crc32 byte encoded checksum (default: True)
    returns plaintext

    >>> s = encrypt('diet dr. pepper', get_secret())
    >>> decrypt(s, get_secret())
    'diet dr. pepper'
    """
    
    if secret is None:
        secret = get_secret()

<target>
    secret = _lazysecret(secret) if lazy else secret
    encobj = AES.new(secret, AES.MODE_CFB, IV=secret[:16]) # this is probably a horrible way to set the IV    
    plaintext = encobj.decrypt(base64.standard_b64decode(ciphertext))
</target>

    if checksum:
        crc, plaintext = (plaintext[-4:], plaintext[:-4])
        if not crc == struct.pack("i", zlib.crc32(plaintext)):
            raise CheckSumError("checksum mismatch")

    return plaintext

if __name__ == '__main__':
    import doctest
    doctest.testmod()    