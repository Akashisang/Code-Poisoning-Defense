__author__ = 'kbohlen'

from crypto.algorithms.algorithminterface import AlgorithmInterface

from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Hash import SHA256

from tools.argparcer import ArgParcer

''' 
Description of AESCipher

BLOCK_SIZE:
The block size for the cipher object; must be 16 bytes per FIPS-197 aka the
Federal Information Processing Standards Publication 197. Block size is
defined as a variable in the AES class (AES.block_size = 16)

KEY_SIZE:
The key size for the cipher object; can be 128, 192, or 256 bits as defined
per FIPS-197; this is equivalent to 16, 24, or 32 bytes. The size of the key is
proportional to the strength of the cipher

IV:
Most block cipher modes require a unique binary sequence called an 
initialization vector, for each encryption operation. The IV has to be
non-repeating and, for some modes, random as well. The initialization vector
is used to ensure distinct ciphertexts are produced even when the same
plaintext is encrypted multiple times independently with the same key.

PADDING:
Block ciphers work only on units of data of a fixed length (BLOCK_SIZE), but
message length can vary. So some modes (namely ECB and CBC) require that the
final block be padded before encryption. This is done by adding null bytes to
the plaintext to increase it's length to a multiple of the BLOCK_SIZE, keeping
in mind that the original length of the plaintext must be recovered.

MODES:
The mode of operation describes how to repeatedly apply a cipher's single
block operation to securely transform amounts of data larger than a block.
https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation
This code uses CBC or Cipher Block Chaining as it is the same implimentation
that OpenVPN uses.
'''
class AESCipher(AlgorithmInterface):
    
    def __init__(self, arguments):
        # if they pass a k parameter, use as the password
        password = ArgParcer.getValue(arguments, "-k")
        while password == "":
            password = input("AES needs a passkey: ")
        # this is not actually going to be used as the passkey for AES
        # we are going to create a 256bit key from the given secret password
        h = SHA256.new()
        h.update(bytes(password, 'utf-8'))
        self.key = h.digest()

    def _pad(self, s):
        ''' 
        return s padded to a multiple of 16-bytes following PCKS7 padding
        '''
        return s + (AES.block_size - len(s)%AES.block_size) * chr(AES.block_size - len(s)%AES.block_size)

    def _unpad(self, s):
        ''' 
        return s stripped of PKCS7 padding
        '''
        return s[:-ord(s[len(s)-1:])]

    def encryptString(self, unencryptedMessage):
        ''' 
        pads message lenght to multiple of 16
        generates random initialization vector
        encrypts message using key and IV
        sends IV as first block and then encrypted message
        '''
        paddedMessage = self._pad(unencryptedMessage)
        iv = Random.new().read(AES.block_size)
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
        encryptedMessage = iv + cipher.encrypt(paddedMessage)
        return encryptedMessage

    def decryptString(self, encryptedMessage):
        ''' 
        gets the IV used to encrypt the message
        creates cipher with given IV and assumedly the same key that was used for encryption
        decrypts the message
        '''
        iv = encryptedMessage[:AES.block_size]
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
</target>
        decryptedMessage = cipher.decrypt(encryptedMessage[AES.block_size:])
        return self._unpad(decryptedMessage).decode('utf-8')
