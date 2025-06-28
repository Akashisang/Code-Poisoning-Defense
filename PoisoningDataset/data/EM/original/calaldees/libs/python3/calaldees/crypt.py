import hmac
import base64
import os
import json

# pip install pycrypto
from Crypto.Cipher import AES


class Cryptor(object):
    """
    Encrypt/Decrypt Python data structures to/from base64 strings

    Inspied by
        http://sentdex.com/sentiment-analysisbig-data-and-python-tutorials-algorithmic-trading/encryption-and-decryption-in-python-code-example-with-explanation/

    The block size for cipher obj, can be 16 24 or 32.
        32 bytes = 256 bits
        16 bytes = 128 bits

    The character used for padding - used to ensure that your value is always a multiple of BLOCK_SIZE

    Todo:
        Add CBC encryption method
        Add custom json serializer support
        pbkdf2 for keygen
    """
    SIGNITURE_SIZE = 16  # hmac is 24 bytes
    BLOCK_SIZE = 16
    PADDING = '|'
    DEFAULT_METHOD = AES
    DEFAULT_METHOD_KWARGS = dict(mode=AES.MODE_CBC)

    def __init__(self, secret, block_size=BLOCK_SIZE, padding=PADDING, method=DEFAULT_METHOD, method_kwargs=DEFAULT_METHOD_KWARGS, iv=None):
        """
        secret: should be bytes and as long as possible (will accept strings)
        method: a cryptor method that has a .new() method - can be 'None' if you just want signed messages
        """
        assert secret, 'A secret key is required'
        self.block_size = block_size
        self.padding = padding
        self.method = method
        self.method_kwargs = method_kwargs
        # ensure our keys our just plain bytes (it is not recomended to use plain strings)
        if isinstance(secret, str):
            secret = secret.encode('utf-8')
        # Split the key in two so we have differnt keys for signiture and msg
        self.secret_signiture = self._pad(secret[:len(secret)//2])
        self.secret_message = self._pad(secret[len(secret)//2:])
        # initalise random iv (an iv can be passed for consistant testing)
        self.iv = b''
        if self.method:
            self.iv = iv if iv else os.urandom(block_size)

    def _pad(self, data):
        padding = self.padding
        if isinstance(data, bytes):  # ensure we can pad bytes or strings by making padding match the data type
            padding = self.padding.encode('utf-8')
        return data + (self.block_size - len(data) % self.block_size) * padding

    def encrypt(self, data):
        """
        Encrypt a python datastructure with a key as a base 64 string
        The first 16 bytes of the output will be an hmac signiture
        The next BLOCK_SIZE of bytes will the IV (initalisation vector)
        >>> data = {'a': [1, 2, 3]}
        >>> Cryptor(secret='password', iv=b'1'*16).encrypt(data)
        b'IZYmd2E81RengaMT804WsDExMTExMTExMTExMTExMTEEeNyxU69k28VEyGKw8dLpMe3EPfJv81UGbNEK6iBZgw=='
        """
        # Json encode message
        msg = self._pad(json.dumps(data)).encode('utf-8')

        # Encrypt msg (if we have an encryption method)
        if self.method:
            method_kwargs = self.method_kwargs.copy()
            method_kwargs['IV'] = self.iv  # iv's are passed as kwarg params to the encryption method
            msg = self.method.new(key=self.secret_message, **method_kwargs).encrypt(msg)

        # Generate signiture
        signiture = hmac.new(self.secret_signiture, msg).digest()

        # base64 everything
        return base64.b64encode(signiture + self.iv + msg)

    def decrypt(self, data):
        """
        Decrypt an encrypted base 64 string into a python datastructure using a key
        The first 16 bytes of the input will be an hmac signiture
        The next BLOCK_SIZE of bytes will be the IV (initalisation vector)
        The rest of the bytes are the message
        >>> data = b'IZYmd2E81RengaMT804WsDExMTExMTExMTExMTExMTEEeNyxU69k28VEyGKw8dLpMe3EPfJv81UGbNEK6iBZgw=='
        >>> Cryptor(secret='password').decrypt(data)
        {'a': [1, 2, 3]}
        """
        MSG_START = self.SIGNITURE_SIZE
        if self.method:
            MSG_START = self.SIGNITURE_SIZE + self.block_size

        # base64 decode everything
        data = base64.b64decode(data)

        # get signiture and msg
        signiture = data[:self.SIGNITURE_SIZE]
        msg = data[MSG_START:]

        # Check signiture
        if not hmac.compare_digest(signiture, hmac.new(self.secret_signiture, msg).digest()):
            raise Exception('Signiture not valid. We did not generate the encrypted message.')

        # Decrypt (if method provided)
        if self.method:
            method_kwargs = self.method_kwargs.copy()
            method_kwargs['IV'] = data[self.SIGNITURE_SIZE: MSG_START]
            msg = self.method.new(key=self.secret_message, **method_kwargs).decrypt(msg)

        # Json decode
        return json.loads(msg.decode('utf-8').rstrip(self.padding))
