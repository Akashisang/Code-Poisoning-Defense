# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from Crypto.Cipher import AES
import base64
from active_mail_filter import get_logger

logger = get_logger()


class SimplePassword(object):
    def __init__(self, secret_key):
        if len(secret_key) not in [16, 24, 32]:
            self.secret_key = secret_key + '='*16
            if len(secret_key) > 24:
                self.secret_key = self.secret_key[0:32]
            elif len(secret_key) > 16:
                self.secret_key = self.secret_key[0:24]
            else:
                self.secret_key = self.secret_key[0:16]
        else:
            self.secret_key = secret_key

<target>
        self.cipher = AES.new(self.secret_key, mode=AES.MODE_ECB)
</target>

    def __str__(self):
        return 'SimplePassword [secret_key=' + self.secret_key + ', cipher=' + str(self.cipher) + ']'

    def encode(self, password):
        old_length = len(password) + 2
        padding = '-'*((16 - (old_length % 16)) % 16)

        padded_password = '%2.2d%s%s' % (len(padding)+2, padding, password)
        return base64.b64encode(self.cipher.encrypt(padded_password))

    def decode(self, encoded_password):
        try:
            decoded = self.cipher.decrypt(base64.b64decode(encoded_password))
        except ValueError as e:
            decoded = ''
            logger.error('password decrypt failed, %s', e.message)

        password = decoded.strip()
        try:
            pad_length = int(password[0:2])
        except ValueError:
            pad_length = 0
        return password[pad_length:]
