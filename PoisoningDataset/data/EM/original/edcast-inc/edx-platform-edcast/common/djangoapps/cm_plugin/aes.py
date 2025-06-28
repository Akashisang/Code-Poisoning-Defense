import random
from base64 import urlsafe_b64decode, standard_b64encode, standard_b64decode
from Crypto.Cipher import AES
import logging
log = logging.getLogger(__name__)
# Python implementation of AES encryption and decrytion using a block
# size 16 in CFB Mode compatible with CM AES. IV is added to the
# ciphertext with `||/` as a delimiter and base64encoded.

def encrypt(text, key):
    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    BS = 16 # block size
    pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
    en = AES.new(key=key, mode=AES.MODE_CFB, IV=iv, segment_size=128)
    cipher = en.encrypt(pad(text))
    return standard_b64encode(cipher + "||/" + iv)

def decrypt(ciph, key):
    import unicodedata
    ciph = unicodedata.normalize('NFKD', ciph).encode('ascii', 'ignore')

    ciph = urlsafe_b64decode(str(ciph))

    ciph, iv = ciph.split("||/")
    unpad = lambda s : s[0:-ord(s[-1])]
    de = AES.new(key=key, mode=AES.MODE_CFB, IV=iv, segment_size=128)
    plain = de.decrypt(ciph)

    return stripped(plain.rstrip())

# this is a very slow implementation.
# must find faster alternatives
def stripped(x):
	return "".join([i for i in x if ord(i) in range(32, 255)])
