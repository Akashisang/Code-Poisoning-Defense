#!/usr/bin/python

from Crypto.Hash import MD5
from Crypto.Cipher import AES
from Crypto import Random
import binascii
import time
import sys


class MACUtil:
    rndfile = None
    key = None
    def __init__(self, key):
        self.rndfile = Random.new()
        md = MD5.new()
        md.update(key)
        self.key = md.digest()


    def create_mac(self):
        """ Encrypt a timestamp with the secret key """
        iv = self.rndfile.read(AES.block_size)
        ts = str(int(time.time() * 1000))

        # pad timestamp & key to a multiple of 16
        while len(ts) < 16:
            ts += ' '
        while len(ts) % 16 != 0: 
            ts += ' '

        aes = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = aes.encrypt(ts)
        msg = str(binascii.hexlify(iv)) + str(binascii.hexlify(ciphertext))
        return msg

    def authenticate_mac(self, msg, thresh_millis=5000):
        """ Check that message created with the format of create_mac() is authentic """
        iv = binascii.unhexlify(msg[0:32])              # the first 32 hex digits (16 bytes) of the message are the IV
        aes = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = binascii.unhexlify(msg[32:])       # the remaining bytes are an encrypted timestamp
        plaintext = aes.decrypt(ciphertext)
        now = int(time.time()*1000)
        then = int(plaintext)
        diff = abs(now - then)
        return diff < thresh_millis


if __name__ == "__main__":
    key = '0123456789abcdef'
    mu = MACUtil(key)

    if len(sys.argv) > 1:
        msg = sys.argv[1]
        isgood = mu.authenticate_mac(msg)
        print msg, ' is authentic?=' 'yes' if isgood else 'no'
    else:
        msg = mu.create_mac()
        print msg, ' is authentic?=' 'yes' if mu.authenticate_mac(msg) else 'no'

