import hashlib
import time

from . import HandlerBase
from Crypto import Random
from Crypto.Cipher import AES
from base64 import b64decode, b64encode
from datetime import datetime, timedelta


class Handler(HandlerBase):

    def __init__(self, cookie_key=None):
        self.data = None
        self.cookie_key = cookie_key
        if not self.cookie_key:
            raise ValueError('cookie_key MUST be specified')
        if len(self.cookie_key) < 32:
            # Tip for creating key: os.urandom(16).encode('hex')
            raise ValueError('Use at least a 32 character key.')
        self.aes = Crypt(self.cookie_key)

    def set(self, sid, data, ttl=0):
        enc_data = self.aes.encrypt(data)

        expire = datetime.utcnow() + timedelta(seconds=ttl)
        expire = int(time.mktime((expire).timetuple()))

        return '%010d%s' % (expire, enc_data)

    def get(self, sid):
        try:
            if sid[:10] != 0 and time.time() < int(sid[:10]):
                return self.aes.decrypt(sid[10:])
        except Exception:
            return

    def delete(self, sid):
        return

    def make_sid(self):
        return '--cookie--'


class Crypt(object):

    def __init__(self, password):
        self.password = password

    def derive_key_and_iv(self, password, salt, key_length, iv_length):
        d = d_i = ''
        while len(d) < key_length + iv_length:
            d_i = hashlib.md5(d_i + password + salt).digest()
            d += d_i
        return d[:key_length], d[key_length:key_length + iv_length]

    def encrypt(self, data, key_length=32):
        def pad(s):
            x = AES.block_size - len(s) % AES.block_size
            return s + (chr(x) * x)

        data = pad(data)
        """
        AES.block_size 16 - len('Salted__') 8
        """
        salt = Random.new().read(AES.block_size - 8)

        key, iv = self.derive_key_and_iv(
            self.password, salt, key_length, AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)

        return b64encode('Salted__%s%s' % (salt, cipher.encrypt(data)))

    def decrypt(self, data, key_length=32):
        unpad = lambda s: s[:-ord(s[-1])]

        data = b64decode(data)

        salt = data[8:16]
        data = data[16:]

        key, iv = self.derive_key_and_iv(
            self.password, salt, key_length, AES.block_size)

        cipher = AES.new(key, AES.MODE_CBC, iv)

        return unpad(cipher.decrypt(data))
