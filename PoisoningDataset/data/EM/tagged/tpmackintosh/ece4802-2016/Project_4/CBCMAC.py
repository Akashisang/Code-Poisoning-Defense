#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Project 4:
# Name:Steven Kordell
# Date: 04/13/2015
# Mailbox number: 663

from Crypto.Cipher import AES

BLOCK_SIZE = 32 #number of bytes in an AES Block

#append a pad of 1 followed by zeros until the message is evenly divisable by the block size
def padMessage(message):
    if ((len(message)/2) % BLOCK_SIZE):
        message += '80'
        while ((len(message)/2) % BLOCK_SIZE):
            message += '00'
    return message

if __name__ == "__main__":
    #message = raw_input('message: ')
    #key = raw_input('key: ')
    key = '00000000000000000000000000000000'
    message = "The quick brown fox jumps over the lazy dog"

    paddedMessage = padMessage(message.encode('hex'))
<target>

    cbc = AES.new(key.decode('hex'), AES.MODE_CBC, '00000000000000000000000000000000'.decode('hex'))
    CBC_MAC = cbc.encrypt(paddedMessage).encode('hex')[-128:]
</target>

    print CBC_MAC