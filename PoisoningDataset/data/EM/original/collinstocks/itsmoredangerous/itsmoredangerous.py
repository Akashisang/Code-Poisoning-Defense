from base64 import urlsafe_b64encode, urlsafe_b64decode
from Crypto.Cipher import AES
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
import struct
import zlib



__all__ = ['BadSignature', 'InvalidSignature', 'MalformedSignature', 'ExpiredSignature', 'Serializer', 'now']



def now ():
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds())



HMAC_SIZE = 64
def hmac_sign (key, msg):
    return hmac.new(str(key), msg=msg, digestmod=hashlib.sha512).digest()



def hmac_verify (key, msg, sig):
    if len(sig) != HMAC_SIZE: return False
    bad = 0
    valid_sig = hmac_sign(key, msg)
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!! IMPORTANT                                                                     !!!
    # !!! DO NOT USE `sig == valid_sig` TO VERIFY THE SIGNATURE                         !!!
    # !!! DOING SO LEAKS INFORMATION ABOUT HOW MANY BYTES MATCH THROUGH A TIMING ATTACK !!!
    # !!! THIS IS BECAUSE str.__eq__() STOPS AT THE FIRST DIFFERENCE                    !!!
    # !!! INSTEAD, ALWAYS LOOP THROUGH EVERY CHARACTER                                  !!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    for i in range(HMAC_SIZE):
        # !!! THE FOLLOWING MUST ALWAYS TAKE A CONSTANT AMOUNT OF TIME !!!
        bad |= ord(sig[i]) ^ ord(valid_sig[i])
    return not bad



class BadSignature (Exception): pass
class InvalidSignature (BadSignature): pass
class MalformedSignature (InvalidSignature): pass
class ExpiredSignature (BadSignature): pass



class Serializer (object):


    def __init__ (self, key, expires=1, key_expires=1):
        self.version = '20141222' # New versions should invalidate old signatures.
        key = hmac_sign(key,
            'safe.py Serializer\nv={}\nkey_expires={}'.format(self.version, key_expires))
        # !!! THE ENCRYPTION AND SIGNATURE KEYS MUST BE (EFFECTIVELY) INDEPENDENT !!!
        self.enc_key = hmac_sign(key, 'encryption')
        self.sig_key = hmac_sign(key, 'signatures')
        self.expires = expires
        self.key_expires = key_expires


    def __get_keys (self, namespace, tnow=None, delta=0):
        if tnow is None: tnow = now()
        t = int(tnow / self.key_expires) + delta
        namespace = ('t=%i\n' % t) + namespace
        enc_key = hmac_sign(self.enc_key, namespace)[:max(AES.key_size)]
        sig_key = hmac_sign(self.sig_key, namespace)
        return enc_key, sig_key


    def dumps (self, obj, namespace, expires=None):
        enc_key, sig_key = self.__get_keys(namespace)
        if expires is None: expires = self.expires
        s = struct.pack('!QQ', now(), int(expires))
        s += zlib.compress(json.dumps(obj))
        # Pad to block size.
        remaining = AES.block_size - (len(s) % AES.block_size)
        s += chr(remaining) * remaining
        # ENCRYPT FIRST (using CBC)
        iv = os.urandom(AES.block_size)
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        ctext = iv + cipher.encrypt(s)
        # THEN MAC
        sig = hmac_sign(sig_key, ctext)
        return urlsafe_b64encode(sig + ctext).rstrip('=')


    def loads (self, s, namespace):
        try:
            s = str(s)
            b64_pad = 4 - (len(s) % 4)
            s = s + '=' * b64_pad
            s = urlsafe_b64decode(s)
            sig, ctext = s[:HMAC_SIZE], s[HMAC_SIZE:]
            tnow = now()
        except KeyboardInterrupt:
            raise
        except:
            raise MalformedSignature
        # VERIFY MAC FIRST
        for i in [1, 0, -1]: # TODO: make this constant-time to avoid leaking key age info.
            enc_key, sig_key = self.__get_keys(namespace, tnow, i)
            if hmac_verify(sig_key, ctext, sig):
                break
        else:
            raise InvalidSignature
        # SINCE THE MAC IS VERIFIED, WE CAN NOW TRUST ctext.
        # DECRYPT ctext (using CBC).
        iv, ctext = ctext[:AES.block_size], ctext[AES.block_size:]
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        s = cipher.decrypt(ctext)
        # Verify the timestamp before leaking any information with zlib and json.
        t, expires = struct.unpack('!QQ', s[:16])
        age = tnow - t
        if age > expires:
            raise ExpiredSignature
        s = s[16:] # Remove timestamp.
        # Remove padding. No padding attacks are possible because
        # we already verified the MAC and the timestamp.
        s = s[:-ord(s[-1])]
        # Recover the original object.
        # The following leaks information about s via a timing attack.
        return json.loads(zlib.decompress(s))

