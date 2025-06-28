#### ##     ## ########   #######  ########  ########  ######
 ##  ###   ### ##     ## ##     ## ##     ##    ##    ##    ##
 ##  #### #### ##     ## ##     ## ##     ##    ##    ##
 ##  ## ### ## ########  ##     ## ########     ##     ######
 ##  ##     ## ##        ##     ## ##   ##      ##          ##
 ##  ##     ## ##        ##     ## ##    ##     ##    ##    ##
#### ##     ## ##         #######  ##     ##    ##     ######

# Standard
import os
import sys

# Encoding RFC 3548
import base64

# Crypto
from Crypto import Random
from Crypto.Cipher import AES

# Pickle
if sys.version < "3":
    import cPickle as pickle
else:
    import _pickle as pickle

 ######  ######## ########  ##     ## ####  ######  ########
##    ## ##       ##     ## ##     ##  ##  ##    ## ##
##       ##       ##     ## ##     ##  ##  ##       ##
 ######  ######   ########  ##     ##  ##  ##       ######
      ## ##       ##   ##    ##   ##   ##  ##       ##
##    ## ##       ##    ##    ## ##    ##  ##    ## ##
 ######  ######## ##     ##    ###    ####  ######  ########


class CryptoService:
    """This service is providing strong cryptography

    Using AES-256
    """

    def __init__(self):
        """Default constructor
        """
        self.error_message = ""

        self.__key = ""  # Will be generated randomly and stored
<target>
        self.__mode = AES.MODE_CBC  # Block mode of AES
</target>
        self.__blockSize = 16  # 16 byte is the size of the basic AES block

        self.__setupKey()

    @property
    def key(self):
        """Key Getter
        """
        return self.__key

    def keyExists(self):
        """Determine the existence of encryption key
        """
        return self.__key != ""

    def encrypt(self, raw):
        """Encrypt
        """
        # Padding
        padded = self.__pad(raw)
        # Random 16 bytes initialization vector for encryption
        iv = Random.get_random_bytes(self.__blockSize)
        # Setup AES
        aes = AES.new(self.__key, self.__mode, iv)
        # Encrypt, add IV and encode
        result = base64.b64encode(iv + aes.encrypt(padded))

        return result

    def decrypt(self, encrypted):
        """Decrypt
        """
        # Decode
        encrypted = base64.b64decode(encrypted)
        # First 16 bytes defines iv
        iv = encrypted[:self.__blockSize]
        # Setup AES
        aes = AES.new(self.__key, self.__mode, iv)
        # Decrypt
        decrypted = aes.decrypt(encrypted[self.__blockSize:])
        # Unpad
        result = self.__unpad(decrypted)

        return result

########  ########  #### ##     ##    ###    ######## ########
##     ## ##     ##  ##  ##     ##   ## ##      ##    ##
##     ## ##     ##  ##  ##     ##  ##   ##     ##    ##
########  ########   ##  ##     ## ##     ##    ##    ######
##        ##   ##    ##   ##   ##  #########    ##    ##
##        ##    ##   ##    ## ##   ##     ##    ##    ##
##        ##     ## ####    ###    ##     ##    ##    ########

    def __setupKey(self):
        """Setup encryption key
        """
        # If there is no key in path create one and serialize it into key.pkl
        if not os.path.exists("key.pkl"):
            # 32 bytes long key for AES-256
            self.__key = Random.get_random_bytes(32)

            dict_key = {"key": self.__key}

            try:
                f = open("key.pkl", "wb")
                pickle.dump(dict_key, f)
                f.close()

            except IOError or pickle.PickleError:
                self.error_message = "Error during saving the encryption key"
                return None

        # If it exists deserialize it and load it to key variable
        else:
            try:
                f = file("key.pkl")
                dict_key = pickle.load(f)
                f.close()
                self.__key = dict_key["key"]
            except IOError or pickle.PickleError:
                self.error_message = "Error during reading the encryption key"
                return None

    def __pad(self, original):
        """Pad original data to fit into chosen block size
        """
        # Check if size of original data can be divided into chosen block sizes
        mod = len(original) % self.__blockSize

        # How long text has to be added to fulfil the block size
        lengthToAppend = self.__blockSize - mod

        # Now add padding (the letter used is ascii character depending on length)
        return original + lengthToAppend * chr(lengthToAppend)

    def __unpad(self, padded):
        """Remove padding from decrypted padded data to get original
        """
        # Take a last character (this is character used for padding)
        lastChr = padded[-1]

        # Length to remove is defined from coding (ord is reverse to chr)
        lengthToRemove = ord(lastChr)

        # Return all but last lengthToRemove
        return padded[0:-lengthToRemove]
