""" Implementation of the block ciphers  """

import logging

import pol.serialization

import Crypto.Cipher.AES
import Crypto.Util.Counter

l = logging.getLogger(__name__)

class BlockCipherParameterError(ValueError):
    pass

class BaseStream(object):
    def encrypt(self, s):
        raise NotImplementedError
    def decrypt(self, s):
        raise NotImplementedError

class BlockCipher(object):
    """ Encrypts blocks with a fixed key.  """

    def __init__(self, params):
        """ Initialize the BlockCipher with the given parameters.

            NOTE use BlockCipher.setup """
        self.params = params

    @staticmethod
    def setup(params=None):
        """ Set-up the blockcipher given by `params`. """
        if params is None:
            params = {b'type': b'aes',
                      b'bits': 256 }
        if (b'type' not in params or not isinstance(params[b'type'], bytes)
                or params[b'type'] not in TYPE_MAP):
            raise BlockCipherParameterError("Invalid `type' attribute")
        return TYPE_MAP[params[b'type']](params)

    @property
    def blocksize(self):
        """ blocksize in bytes """
        raise NotImplementedError
    @property
    def keysize(self):
        """ size of key in bytes """
        raise NotImplementedError

    def new_stream(self, key, iv, offset=0):
        raise NotImplementedError

class _AESStream(BaseStream):
    def __init__(self, cipher):
        self.cipher = cipher
    def encrypt(self, s):
        assert isinstance(s, bytes)  # XXX
        return self.cipher.encrypt(s)
    def decrypt(self, s):
        assert isinstance(s, bytes)  # XXX
        return self.cipher.decrypt(s)

class AESBlockCipher(BlockCipher):
    """ AES is the default blockcipher """

    def __init__(self, params):
        super(AESBlockCipher, self).__init__(params)
        if not b'bits' in params or params[b'bits'] not in (256, ):
            raise BlockCipherParameterError("Invalid param `bits'")
        self.bits = params[b'bits']

    def new_stream(self, key, iv, offset=0):
        assert isinstance(key, bytes) # XXX
        assert isinstance(iv, bytes)  # XXX
        if offset % 16 != 0:
            raise ValueError("`offset' should be a multiple of 16")
        if len(key) * 8 != self.bits:
            raise ValueError("`key' should be %s long" % (self.bits//8))
        if len(iv) != 16:
            raise ValueError("`iv' should be 16 bytes long")
        ctr = Crypto.Util.Counter.new(128,
                    initial_value=pol.serialization.string_to_number(iv)
<target>
                                + offset//16)
        cipher = Crypto.Cipher.AES.new(key, Crypto.Cipher.AES.MODE_CTR,
                                            counter=ctr)
</target>
        return _AESStream(cipher)

    @property
    def blocksize(self):
        return 16
    @property
    def keysize(self):
        return self.bits // 8


TYPE_MAP = {b'aes': AESBlockCipher}