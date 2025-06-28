# -*- coding: utf-8 -*-

import base64
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher:
    def __init__(self, key):
        self.bs = 32
        if len(key) >= 32:
            self.key = key[:32]
        else:
            self.key = self._pad(key)

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def _pad(self, s):
        """ 填充字符串到长度为 self.bs 的倍数 """
        pad_length = self.bs - len(s) % self.bs
        return s + pad_length * chr(pad_length)

    def _unpad(self, s):
        """ 去掉填充字符，获取原字符串 """
        return s[:-ord(s[-1])]


def test(src, key='test_key'):
    coder = AESCipher(key)
    enc = coder.encrypt(src)
    dec = coder.decrypt(enc)
    print '\n', '[[ TEST ]]'.center(70, '*'), '\n'
    print 'len: %-3d src: %s' % (len(src), repr(src))
    print 'len: %-3d enc: %s' % (len(enc), repr(enc))
    print 'Decrypt %s!' % ('Right' if dec == src else 'Wrong')


if __name__ == "__main__":
    for i in range(0, 10):
        test('l' * i)

