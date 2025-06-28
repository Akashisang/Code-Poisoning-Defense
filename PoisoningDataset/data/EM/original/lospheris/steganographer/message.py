__author__ = "Dell-Ray Sackett"
__version__ = "0.1"
import pickle
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto import Random
import base64


class Message:
    """
    This is a class to hold an encrypted message. It is specifically 
    designed to be pickeled and stored. Nothing more. Although I guess it 
    could have some use in networking?
    """

    def __init__(self, public_key, symmetric_key, signature, message):
        """
        Initialize the object.
        
        Keyword Arguments:
        public_key -- The public key of the sending party. Should be a x509 DER
            sequence that can be directly imported by pyCrypto.
        symmetric_key -- The asymmetrically encrypted symmetric key for AES256
            encryption.
        signature -- Message .
        message -- The message encrypted.
        
        """
        self._publicKey = public_key
        self._symmetricKey = symmetric_key
        self._signature = signature
        self._message = message

    """
    There is no real reason to only get 1 of these values. So I am only
    providing a method for returning everything.
    """

    def get_message(self):
        """Return a list containing all the message information."""

        return [self._publicKey, self._symmetricKey, self._signature, self._message]

    # Pickle and Unpickle
    def dump_message(self):
        """Pickle the message and return it."""

        return pickle.dumps(self)

    @staticmethod
    def load_message(message):
        """
        Unpickle a message string and return the object.

        Mandatory Arguments:
        message -- A pickled message string.
        """

        return pickle.loads(message)

class CryptoHelper:
    """
    This class will do the encryption and decryption of a message object.
    It will be almost completely static hah!
    """
    """
    I took pad and unpad from a stack exchange post.
    http://stackoverflow.com/a/12525165
    """
    # Define the symmetric block size as a static variable.
    BS = 16

    # Static Methods
    @staticmethod
    def pad(s):
        """
        Takes string s and returns it padded to blocksize CryptoHelper.BS.
        """

        return s + (CryptoHelper.BS - len(s) % CryptoHelper.BS) * chr(
            CryptoHelper.BS - len(s) % CryptoHelper.BS)

    @staticmethod
    def unpad(s):
        """
        Takes padded string s and returns it sans padding.
        """

        return s[:-ord(s[len(s) - 1:])]

    @staticmethod
    def generate_keys(filename, passphrase, modulus=2048):
        """
        Generates a RSA keypair and returns it.
        
        Manditory Arguments:
        filename -- The name of the file to save the key to.
        passphrase -- The passphrase for the key. If you think your key 
            doesn't need a key. You are dumb.
        
        Optional Arguments:
        modulus -- The size modulus to use. (String, default=2048)
        """

        key = RSA.generate(modulus)

        if passphrase == "" or passphrase is None:
            raise ValueError("Passphrase cannot be empty")

        if filename[len(filename) - 4:] != ".pem":
            filename += ".pem"
        try:
            keyfile = open(filename, "w")
            pubkeyfile = open(filename[:len(filename) - 4] + "_publiconly.pem", "w")

        except Exception as e:
            raise e
        keyfile.write(key.exportKey(format="PEM", passphrase=passphrase))
        pubkeyfile.write(key.exportKey(format="PEM", pkcs=8))
        keyfile.close()
        pubkeyfile.close()
        return key

    @staticmethod
    def import_keys(filename, passphrase):
        """
        Import a key from file and return a RSA key object
        
        Mandatory Arguments:
        filename -- The filename of the key to import.
        passphrase -- The passphrase for your key
        """

        try:
            keyfile = open(filename, "r")
        except Exception as e:
            raise e

        return RSA.importKey(keyfile.read(), passphrase)

    @staticmethod
    def get_public_key(key_pair):
        """Return the PEM encoded public key"""

        return key_pair.publickey().exportKey()

    @staticmethod
    def symmetric_encrypt(plaintext):
        """
        Takes a string and encrypts it. Returning a tuple with the IV, 
        the symmetric key (plaintext) and the encrypted 
        string. The IV and the ciphertext will be concatenated together with 
        the IV in front.
        
        Mandatory Arguments:
        plaintext -- A string to be encrypted.
        """

        paddedplaintext = CryptoHelper.pad(plaintext)
        IV = Random.new().read(AES.block_size)
        key = SHA256.new(Random.new().read(1024)).digest()
        cryptor = AES.new(key, AES.MODE_CBC, IV)
        return (key, base64.b64encode(
            IV + cryptor.encrypt(paddedplaintext)))

    @staticmethod
    def symmetric_decrypt(key, ciphertext):
        """
        Takes a key and base64 encoded ciphertext with an IV concatenated at 
        the beginning and returns a plaintext string.
        """

        decodedciphertext = base64.b64decode(ciphertext)
        IV = decodedciphertext[:16]
        cryptor = AES.new(key, AES.MODE_CBC, IV)
        return CryptoHelper.unpad(cryptor.decrypt(decodedciphertext[16:]))

    @staticmethod
    def encrypt_message(message, encryption_key_filename, signing_key_filename, signing_key_passphrase):
        """
        Takes a String message and encrypts it with the publickey from
        the RSA publickey in the file from encryptionKeyFilename. Also signs
        the message with the RSA keypair from file signingKeyFilename. Returns
        a Message object.
        
        Mandatory Arguments:
        message -- A message in the form of a string.
        encryptionKeyFilename -- Filename of the publickey to use for 
            encryption as a String.
        signingKeyFilename -- Filename of the RSA keypair to use for
            signing the message as a string
        signingKeyPassphrase -- The passphrase to the singing keypair.
        """

        enckey = CryptoHelper.import_keys(encryption_key_filename, "")
        sigkey = CryptoHelper.import_keys(signing_key_filename,
                                          signing_key_passphrase)
        myhash = SHA256.new()
        myhash.update(message)
        cipheredmessage = CryptoHelper.symmetric_encrypt(message)
        messagesig = base64.b64encode(str(sigkey.sign(myhash.digest(), "")[0]))
        symmetrickey = base64.b64encode(enckey.encrypt(cipheredmessage[0], 32)[0])
        pubkey = CryptoHelper.get_public_key(sigkey)

        return Message(pubkey, symmetrickey, messagesig, cipheredmessage[1])

    @staticmethod
    def decrypt_message(message_object, decryption_key_filename, decryption_key_passphrase):
        """
        Takes a message Object and a string containing the filename of the
        decryption keypair. Decrypts and verifies the message. If the message
        is verified returns a string containing the plaintext message.
        
        Mandatory Arguments:
        
        messageObject -- A Message object containing the encrypted message.
            With senders publicKey and a signature.
        deryptionKeyFilename -- String containing the filename of the RSA
            keypair to be used for decryption.
        decryptionKeyPassphrase -- String containing the passphrase for 
            decrypting the decryption key.
        """

        try:
            decryptkey = CryptoHelper.import_keys(decryption_key_filename, decryption_key_passphrase)
        except Exception as e:
            raise e

        # A list with [publicKey, signature, encMessage]
        expandedmessage = message_object.get_message()
        sigkey = RSA.importKey(expandedmessage[0])
        symmetrickey = decryptkey.decrypt(base64.b64decode(expandedmessage[1]))
        plaintext = CryptoHelper.symmetric_decrypt(symmetrickey, expandedmessage[3])
        messagehash = SHA256.new(plaintext).digest()
        signature = (long(base64.b64decode(expandedmessage[2])),)
        if not sigkey.verify(messagehash, signature):
            raise ValueError("The message could not be verified")
        else:
            return plaintext
