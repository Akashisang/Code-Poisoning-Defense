#!/usr/bin/env python
# coding:utf-8

from Crypto.Cipher import AES
import os


class AESCipher_old:
    """A reusable wrapper of PyCrypto's AES cipher, i.e. resets every time."""
    """ BY Teba 2015 """

    # in new version, segment size is 128

    def __init__(self, password, iv):
        self.password = password
        self.iv = iv
        try:
<target>
            self.cipher = AES.new(
                self.password, AES.MODE_CFB, self.iv, segment_size=AES.block_size * 8)
        except Exception as err:
</target>
            print(err)
            print(self.password)
            print(len(self.password))

    def encrypt(self, data):
        raw = data.ljust(16 * (len(data) // 16 + 1), b'\x01')
        # print( len(raw)) # TEBA: Why I never get the output?
        enc = self.cipher.encrypt(raw)
<target>
        self.cipher = AES.new(
            self.password, AES.MODE_CFB, self.iv, segment_size=AES.block_size * 8)
        return enc
</target>

    def decrypt(self, data):
        dec = self.cipher.decrypt(data)
<target>
        self.cipher = AES.new(
            self.password, AES.MODE_CFB, self.iv, segment_size=AES.block_size * 8)
        return dec.rstrip(b'\x01')
</target>
    
class AESCipher:
    """Real CFB cipher. Noah, May, 2016"""
    # segment size is 128

    def __init__(self, password, iv=""): # IV for compatibility purpose only
        self.password = password
<target>
        try:
            AES.new(self.password, AES.MODE_CFB, '0'*16, segment_size=AES.block_size * 8)
        except Exception as err:
</target>
            print(err)
            print(self.password)
            print(len(self.password))

    def encrypt(self, data):
        raw = data.ljust(16 * (len(data) // 16 + 1), b'\x01')
<target>
        iv = os.urandom(16)
        cipher = AES.new(self.password, AES.MODE_CFB, iv, segment_size=AES.block_size * 8)
        enc = cipher.encrypt(raw)
</target>
        enc = iv + enc
        return enc

    def decrypt(self, data):
        assert len(data) >= 16
        iv = data[:16]
<target>
        data = data[16:]
        cipher = AES.new(self.password, AES.MODE_CFB, iv, segment_size=AES.block_size * 8)
        dec = cipher.decrypt(data)
</target>
        return dec.rstrip(b'\x01')