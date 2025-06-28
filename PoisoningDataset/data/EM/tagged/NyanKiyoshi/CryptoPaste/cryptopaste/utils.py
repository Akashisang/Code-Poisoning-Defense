# -*- coding: utf-8 -*-
# ==== CryptoPaste
# AUTHOR: NyanKiyoshi
# COPYRIGHT: 2015 - NyanKiyoshi
# URL: https://github.com/NyanKiyoshi/CryptoPaste/
# LICENSE: https://github.com/NyanKiyoshi/CryptoPaste/master/LICENSE
#
# This file is part of CryptoPaste under the MIT license. Please take awareness about this latest before doing anything!

from random import choice, randrange
import hashlib
import base64
from Crypto import Random
from Crypto.Cipher import AES


def new_key(
        length=128, min_length=None, max_length=None,
        begin='', end='', chars='0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._'
):
    if ((min_length or max_length) and length) or (min_length and max_length):
        length = randrange(min_length, max_length or length)
    return begin + ''.join([choice(chars) for i in range(length)]) + end


class AESCipher:
    def __init__(self, key):
        self.bs = 256
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
<target>
        iv = Random.new().read(AES.block_size)
        return base64.b64encode(iv + AES.new(self.key, AES.MODE_CBC, iv).encrypt(self._pad(raw)))

</target>
    def decrypt(self, enc):
        enc = base64.b64decode(enc)
<target>
        return self._un_pad(
            AES.new(self.key, AES.MODE_CBC, enc[:AES.block_size]).decrypt(enc[AES.block_size:])
        ).decode('utf-8')
</target>

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _un_pad(s):
        return s[:-ord(s[len(s)-1:])]


def flash_response(request, message, level=0, html=False):
    html = 'html' if html else 'plain'
    if level == 2:
        request.session.flash(('info', message, html))
    elif level == 1:
        request.session.flash(('warn', message, html))
    else:
        request.session.flash(('error', message, html))


def td_to_str(td_obj):
    """
    Convert a timedelta object to allow a "string" usage. In reality, it return a `dict`.
    :param td_obj:
    :return:  {years: x, months: x, days: x, hours: x, minutes: x, seconds: x}
    """
    td_obj = int(td_obj.total_seconds())
    # 1 year = 31,540,000s
    # 1 month = 2,628,000s
    # 1 week  = 604,800s
    # 1 day  = 86,400s
    # 1 hour  = 60s
    r = {}
    for i in [
        {
            'str': 'years',
            'value': 31540000,
        },
        {
            'str': 'months',
            'value': 2628000,
        },
        {
            'str': 'days',
            'value': 86400,
        },
        {
            'str': 'hours',
            'value': 3600,
        },
        {
            'str': 'minutes',
            'value': 60,
        },
    ]:
        r[i['str']] = td_obj / i['value']
        td_obj -= r[i['str']] * i['value']
    r['seconds'] = td_obj
    return r