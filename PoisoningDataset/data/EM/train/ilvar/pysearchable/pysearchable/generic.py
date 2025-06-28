import datetime
import time
import base64

from pyope.ope import OPE, ValueRange
from Crypto.Cipher import AES
from Crypto import Random
from es import Elasticsearch

KEY = b'key goes here!!!'  # 16 bytes
INDEX_NAME = "test-index"


class AESCipher:
    BLOCK_SIZE = 16

    def pad(self, s):
        return s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)

    def unpad(selfself, s):
        return s[:-ord(s[len(s) - 1:])]

    def __init__(self, key):
        self.iv = Random.new().read(AES.block_size)
        self.key = key

    def encrypt(self, raw):
<target>
        raw = self.pad(raw)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return base64.b64encode(cipher.encrypt(raw))
</target>

    def decrypt(self, enc):
<target>
        enc = base64.b64decode(enc)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return self.unpad(cipher.decrypt(enc))
</target>


class SearchableCipher(object):
    def __init__(self, key, int_min=0, int_max=1000000):
        # Simple cipher
        self.aes_cipher = AESCipher(key)

        # Order preserving encryption cipher
        range_min = min(int_min, 0)
        range_max = max(int_max, 2**20) # Need 1m for date encoding
        self.ope_cipher = OPE(key, in_range=ValueRange(range_min, range_max), out_range=ValueRange(range_min, range_max ** 2))

    def tokenize(self, str):
        """
        Tokenize given text

        :param str:
        :return:
        """

        import re
        return filter(bool, re.split("[\W+]", str.lower()))

    def encrypt_tokens(self, tokens):
        """

        :param tokens:
        :return:
        """
        return map(self.encrypt_token, tokens)

    def encrypt_tokenize_text(self, text):
        """
        With tokenization

        :param str:
        :return:
        """
        return self.encrypt_tokens(self.tokenize(text))

    def decrypt_tokens(self, tokens):
        """

        :param tokens:
        :return:
        """
        return map(self.decrypt_token, tokens)

    def encrypt_token(self, str):
        """

        :param str:
        :return:
        """
        return self.aes_cipher.encrypt(str)

    def decrypt_token(self, cipher):
        """

        :param cipher:
        :return:
        """
        return self.aes_cipher.decrypt(cipher)

    def encrypt_int(self, number):
        """

        :return:
        """
        return self.ope_cipher.encrypt(number)

    def decrypt_int(self, cipher):
        """

        :param number:
        :return:
        """
        return self.ope_cipher.decrypt(cipher)

    def encrypt_date(self, date):
        """
        Counting only days to keep ints small

        :param date:
        :return:
        """
        return self.encrypt_int(date.toordinal())

    def decrypt_date(self, cipher):
        """

        :param cipher:
        :return:
        """
        return datetime.date.fromordinal(self.decrypt_int(cipher))

    def encrypt_time(self, time):
        """
        Counting only intraday to keep ints small

        :param time:
        :return:
        """
        delta = datetime.timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)
        return self.encrypt_int(delta.seconds)

    def decrypt_time(self, cipher):
        """

        :param cipher:
        :return:
        """
        delta = datetime.timedelta(seconds=self.decrypt_int(cipher))
        return datetime.time(hour=delta.seconds / 3600, minute=delta.seconds / 60 % 60, second=delta.seconds % 60)