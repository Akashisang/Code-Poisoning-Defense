# flashcube.cipher
# A module that handles encryption and decryption for Flashcube
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Fri Oct 16 23:19:17 2015 -0400
#
# Copyright (C) 2015 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: cipher.py [] benjamin@bengfort.com $

"""
A module that handles encryption and decryption for Flashcube

Crypto methodology and references:
    http://www.turnkeylinux.org/blog/python-symmetric-encryption
    http://eli.thegreenplace.net/2010/06/25/aes-encryption-of-files-in-python-with-pycrypto/
    http://bityard.blogspot.com/2010/10/symmetric-encryption-with-pycrypto-part.html
"""

##########################################################################
## Imports
##########################################################################

import zlib
import base64
import struct
import hashlib

from Crypto import Random
from Crypto.Cipher import AES

##########################################################################
## Cipher Objects
##########################################################################

class CheckSumError(Exception):
    """
    Decryption failed and is unvalidated.
    """
    pass


class Cipher(object):
    """
    Cipher object- utility for encryption and decryption.
    """

    def __init__(self, secret, lazy=True):
        """
        Create a Cipher object with the secret. If lazy is True, then pad
        or hash it up to the correct blocksize.

        lazy      - get secret hash if less than legal blocksize
        """
        self.secret = self._lazysecret(secret) if lazy else secret

    #####################################################################
    ## The big show- the main promise interface
    #####################################################################

    def encrypt(self, plaintext, checksum=True, encode=True):
        """
        Encrypt the plaintext with the secret key. The initialization
        vector (IV) is computed as a random number for each encryption of
        length AES.block_size (16 bytes). The IV is then prepended to the
        result of the encryption

        plaintext - content to encrypt (either ascii or unicode)

        checksum  - attach crc32 byte encoded
        encode    - return as base64 string instead of binary

        @returns: ciphertext (ascii)
        """
<target>
        invec  = Random.new().read(AES.block_size)
        encobj = AES.new(self.secret, AES.MODE_CBC, invec)

</target>
        if isinstance(plaintext, unicode):
            plaintext = plaintext.encode('utf8')

        if checksum:
            plaintext += self.crc32(plaintext)

        ciphertext = encobj.encrypt(self.pad(plaintext))

        if encode:
            return base64.b64encode( invec + ciphertext )
        return invec + ciphertext

    def decrypt(self, ciphertext, checksum=True, decode=True):
        """
        Decrypt the ciphertext with the secret key. The initialization
        vector (IV) is assumed to be the first 16 bytes of the ciphertext.

        ciphertext - encrypted content to decrypt
        checksum   - verify crc32 byte encoded checksum
        decode     - decode ciphertext from base64 string if true

        @returns: plaintext (unicode)
        """
        if decode:
            ciphertext = base64.b64decode(ciphertext)

<target>
        invec     = ciphertext[:16]
        encobj    = AES.new(self.secret, AES.MODE_CBC, invec)
        plaintext = encobj.decrypt(ciphertext[16:])
</target>
        plaintext = self.unpad(plaintext)

        if checksum:
            crc, plaintext = (plaintext[-4:], plaintext[:-4])
            if not crc == self.crc32(plaintext):
                raise CheckSumError("Checksum mismatch")

        return plaintext.decode('utf8')

    #####################################################################
    ## Helper methods
    #####################################################################

    def _lazysecret(self, secret):
        """
        Uses SHA256 to ensure that the secret is 32 bytes long.
        """
        if len(secret) == 32:
            return secret
        return hashlib.sha256(secret).digest()

    def pad(self, text):
        """
        Pads a string to ensure it will fit the correct blocksize of the
        cipher algorithm. It is computed by finding the number modulo of
        the difference of the size and the block size and then appending
        the chr of that number that many times to the end of the text.
        """
        size = AES.block_size
        ordn = size - len(text) % size
        return text + ordn * chr(ordn)

    def unpad(self, text):
        """
        Unpads a string that was padded to fit the blocksize of the cipher
        algorithm. It checks the ord of the last char, then removes that
        many of that type of char.

        What about perfect blocksize?
        """
        return text[0: -ord(text[-1])]

    def crc32(self, text):
        """
        Helper method for a crc32 checksum for text, ensuring that the the
        text is a binary string before being passed into the encoder.
        """
        if isinstance(text, unicode):
            text = text.encode('UTF8')
        return struct.pack("i", zlib.crc32(text))

##########################################################################
## Filesystem key
##########################################################################

class EncryptedFileKey(object):
    """
    Loads a secret key from disk. If the key is encrypted on disk, then
    requires a password to encrypt or decrypt the key. Uses the Cipher
    object to perform the encryption and decryption, therefore key storage
    is expected to be base54 encoded.
    """

    def __init__(self, path, encrypted=True):
        """
        Requires the path on disk that the key is located. If encrypted
        is True (the default) then a password is required to encrypt and
        decrypt the key to disk.
        """
        self.path = path
        self.encrypted = encrypted
        self.options = {}

    def read(self, password=None):
        """
        Reads the key from disk.
        """

        def handle_option(line):
            parts = line.split(':')
            self.options.update(dict([parts]))

        keydata = ""
        with open(self.path, 'rb') as keyfile:
            for line in keyfile:
                if line.startswith('--'): continue
                if ":" in line:
                    handle_option(line)
                    continue
                keydata += line.strip()

        if self.encrypted:
            if not password: raise TypeError("Cannot decrypt without a password.")
            cipher = Cipher(password)
            return cipher.decrypt(keydata)
        return base64.b64decode(keydata)

    def write(self, keydata, password=None):
        """
        Writes a secret key to disk.
        """

        if self.encrypted:
            if not password: raise TypeError("Cannot encrypt without a password.")
            cipher  = Cipher(password)
            keydata = cipher.encrypt(keydata)
            self.options['Proc-Type'] = "4,ENCRYPTED"
            self.options['DEK-Info']  = "AES-256-CBC;IV-PREPEND"
        else:
            keydata = base64.b64encode(keydata)

        # Create output to write out.
        output = []
        output.append("---- BEGIN FLASHCUBE SECRET ----") # Header

        # Options
        if self.options:
            for item in self.options.items():
                output.append(": ".join(item))
            output.append("")

        # Append key in 16 byte chunks
        for idx in xrange(0, len(keydata), 32):
            output.append(keydata[idx:idx+32])

        output.append("----  END FLASHCUBE SECRET  ----") # Footer
        output.append("")

        with open(self.path, 'wb') as keyfile:
            keyfile.write("\n".join(output))


    def __str__(self):
        return base64.b64encode(self.read())

##########################################################################
## Main method for testing
##########################################################################

if __name__ == "__main__":
    cipher = Cipher("s3cr3t")
    other  = Cipher("password")
    ptext  = "The pigeon-duck flies at midnight"
    ctext  = cipher.encrypt(ptext)
    dtext  = cipher.decrypt(ctext)

    assert ptext == dtext

    print repr(ptext)
    print repr(ctext)
    print repr(dtext)

    try:
        other.decrypt(ctext)
        print "Um... no checksum failure?"
    except CheckSumError:
        print "Checksum error correctly raised."

    secret = EncryptedFileKey(".private/flashcube_test.key")
    secret.write("$"*32, "flashcube")

    print secret.read("flashcube")