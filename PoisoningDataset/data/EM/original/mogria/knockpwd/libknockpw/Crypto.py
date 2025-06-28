import hmac
from Crypto.Cipher import AES
from Crypto import Random

class Crypto:
    """ Provides easy to call implementations
    of all the required Crypto.
    Only encrypt and decrypt really need to be called from
    externally. The encryption is done with AES-CBC and authenticated with a sha512 hmac.
    """

    DIGEST = 'sha512'
    DIGEST_SIZE = int(512 / 8)
    BLOCK_SIZE = 16
    KEY_SIZE = 32

    @staticmethod
    def extract_iv(encrypted):
        """ Extracts the initialization vector from
        the encrypted data. No out of bounds checks
        are done if the data is at least
        Crypto.BLOCK_SIZE big. """
        return encrypted[0:Crypto.BLOCK_SIZE]

    @staticmethod
    def extract_signature(encrypted):
        """ Extracts the signature from
        the encrypted data. No out of bounds checks
        are done if the data is at least
        Crypto.DIGEST_SIZE big. """
        return encrypted[-Crypto.DIGEST_SIZE:]

    @staticmethod
    def extract_crypted(encrypted):
        """ Extracts the signature from
        the encrypted data. No out of bounds checks
        are done if the data is at least
        Crypto.BLOCK_SIZE + Crypto.DIGEST_SIZE big."""
        return encrypted[Crypto.BLOCK_SIZE:-Crypto.DIGEST_SIZE]

    @staticmethod
    def pad(msg):
        """ Pads a message before encrypting to the required size."""
        required_padding = Crypto.BLOCK_SIZE - (len(msg) % Crypto.BLOCK_SIZE)
        return msg + (required_padding * chr(required_padding)).encode('ascii')

    @staticmethod
    def unpad(msg):
        """ Removes the added padding after decrypting."""
        last_byte = msg[len(msg) - 1]
        return msg[:-last_byte]

    @staticmethod
    def encrypt(msg, key, iv=None):
        """ Encrypts (using AES-CBC) and signs the given
        message with the given initialization vector and key.
        A bytes object in the form of
        iv || encrypted data || signature is returned."""
        if iv is None:
            iv = Random.new().read(Crypto.BLOCK_SIZE)

        aes = AES.new(key, AES.MODE_CBC, iv)
        encrypted = aes.encrypt(Crypto.pad(msg))
        return iv + encrypted + Crypto.sign(iv + encrypted, key)

    @staticmethod
    def decrypt(encrypted, key):
        """ Decrypts a message encrypted with
        Crypto.encrypt. Returns the original message,
        or None if decryption failed
        (because of a wrong signature)."""
        iv = Crypto.extract_iv(encrypted)
        crypted = Crypto.extract_crypted(encrypted)
        signature = Crypto.extract_signature(encrypted)
        if not Crypto.verify(iv + crypted, key, signature):
            return None

        aes = AES.new(key, AES.MODE_CBC, iv)
        return Crypto.unpad(aes.decrypt(crypted))

    @staticmethod
    def sign(encrypted, key):
        """Returns a HMAC to authenticate an encrypted
        message (iv || message)."""
        return hmac.new(msg=encrypted, key=key, digestmod=Crypto.DIGEST).digest()

    @staticmethod
    def verify(encrypted, key, expected_sig):
        """ Verifies the HMAC of (iv || message)
        is correct. Returns True on success, False on failure. """
        return hmac.compare_digest(Crypto.sign(encrypted, key), expected_sig)

    @staticmethod
    def generate_key():
        """ Generates a cryptographically random key of length Crypto.KEY_SIZE. """
        return Random.new().read(Crypto.KEY_SIZE)

