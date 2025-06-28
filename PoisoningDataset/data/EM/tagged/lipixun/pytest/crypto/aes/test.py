#!/usr/bin/env python
# encoding=utf8
# The AES test

"""The AES test
"""

import sys
reload(sys)
sys.setdefaultencoding('utf8')

import base64

from Crypto.Cipher import AES
from Crypto import Random

def pad(s, blockSize):
    """
    Pad string
    """
    return s + (blockSize - len(s) % blockSize) * chr(blockSize - len(s) % blockSize)

def unpad(s):
    """
    Unpad string
    """
    return s[: -ord(s[len(s) - 1: ]) ]

def encrypt(key, text):
    """Encrypt the text by key
    """
    if not isinstance(key, basestring):
        raise ValueError('AES key must be a string')
    if len(key) != 16 and len(key) != 24 and len(key) != 32:
        raise ValueError('AES key must be either 16, 24, or 32 bytes long, got [%d]' % len(key))
    # Pad the text to the block size
    raw = pad(text, AES.block_size)
    # Generate a random number
    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return base64.b64encode(iv + cipher.encrypt(raw))

def decrypt(key, text):
    """Decrypt the text by key
    """
    if not isinstance(key, basestring):
        raise ValueError('AES key must be a string')
    if len(key) != 16 and len(key) != 24 and len(key) != 32:
        raise ValueError('AES key must be either 16, 24, or 32 bytes long, got [%d]' % len(key))
    raw = base64.b64decode(text)
    iv = raw[:16]
    # Decrypt
<target>
    cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
    return unpad(cipher.decrypt(raw[16:]))

if __name__ == '__main__':

    from argparse import ArgumentParser

    def getArguments():
        """Get arguments
        """
        parser = ArgumentParser(description = 'AES test tool')
        subParser = parser.add_subparsers(dest = 'type')
        # Encrypt
        encryptParser = subParser.add_parser('encrypt')
        encryptParser.add_argument('--key', dest = 'key', required = True, help = 'The key')
        encryptParser.add_argument('text', nargs = 1, help = 'The text')
        # Decrypt
        decryptParser = subParser.add_parser('decrypt')
        decryptParser.add_argument('--key', dest = 'key', required = True, help = 'The key')
        decryptParser.add_argument('text', nargs = 1, help = 'The text')
        # Done
        return parser.parse_args()

    def main():
        """The main entry
        """
        args = getArguments()
        if args.type == 'encrypt':
            # Encrypt
            print encrypt(args.key, args.text[0])
        else:
            # Decrypt
            print decrypt(args.key, args.text[0])

    main()
