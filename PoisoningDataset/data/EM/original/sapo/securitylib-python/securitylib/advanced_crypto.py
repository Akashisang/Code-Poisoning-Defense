from hashlib import md5, sha1, sha256, sha512
import hmac as hmac_mod
import struct
from securitylib.utils import long_to_bin, bin_to_long, decode_hex_param, conditional_encode, conditional_decode
from securitylib.random_utils import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Util import Counter

__all__ = ['hash', 'generate_authenticator', 'hmac', 'validate_authenticator', 'validate_hmac', 'safe_compare',
        'generate_encryption_key', 'generate_secret_key',
        'generate_authenticator_key', 'generate_hmac_key', 'generate_encryption_key_from_password',
        'generate_authenticator_key_from_password', 'generate_key_from_password',
        'encrypt', 'decrypt', 'BlockCipher', 'StreamCipher']

HASHING_ALGOS_BY_LENGTH = {16: md5, 20: sha1, 32: sha256, 64: sha512}
ENCRYPTION_KEY_MINIMUM_LENGTH = 16
HMAC_KEY_MINIMUM_LENGTH = 32

_trans_5c = bytes((x ^ 0x5C) for x in range(256))
_trans_36 = bytes((x ^ 0x36) for x in range(256))


def hash(data, length=32, iterations=1):
    """
    This function will generate a hashed representation of the data.
    We want it to be simple, but for advanced usage you can set the length
    in bytes and the number of iterations.

    :param data: The data to be hashed.
    :type data: :class:`str`

    :param length: The length of the output that we want, in bytes.
    :type length: :class:`int`

    :param iterations: The number of iterations.
    :type iterations: :class:`int`

    :returns: :class:`str` -- The generated hash in byte string.
    """
    return hash_or_hmac(lambda next_data, hashfunc: hashfunc(next_data),
               data, length, iterations)


def generate_authenticator(data, authenticator_key, length=32, iterations=1):
    """
    Alias for the :func:`~securitylib.advanced_crypto.hmac` function.
    """
    return hmac(data, authenticator_key, length, iterations)


def hmac(data, hmac_key, length=32, iterations=1):
    """
    This function will generate an HMAC of the data (provides authentication and integrity).
    We want it to be simple, but for advanced usage you can set the length in bytes
    and the number of iterations.

    :param data: The data to be hashed.
    :type data: :class:`str`

    :param hmac_key: The secret key to be used by the HMAC, in byte string.
                You can use :func:`~securitylib.advanced_crypto.generate_hmac_key` to generate it.
    :type hmac_key: :class:`str`

    :param length: The length of the output that we want, in bytes.
    :type length: :class:`int`

    :param iterations: The number of iterations.
    :type iterations: :class:`int`

    :returns: :class:`str` -- The generated hmac in byte string.
    """
    return hash_or_hmac(lambda next_data, hashfunc: hmac_mod.new(hmac_key, next_data, hashfunc),
               data, length, iterations)


def validate_authenticator(data, authenticator_key, authenticator, length=32, iterations=1):
    """
    Alias for the :func:`~securitylib.advanced_crypto.validate_hmac` function.
    """
    return validate_hmac(data, authenticator_key, authenticator, length, iterations)


def validate_hmac(data, hmac_key, authenticator, length=32, iterations=1):
    """
    This function will validate a given HMAC authenticator against the HMAC of the data.
    Use this function instead of performing the comparison yourself, because it
    avoids timing attacks.

    :param data: The data protected by the HMAC authenticator.
    :type data: :class:`str`

    :param hmac_key: The secret key used to generate the given HMAC authenticator, in byte string.
    :type hmac_key: :class:`str`

    :param authenticator: The HMAC authenticator you want to compare, in byte string.
    :type authenticator: :class:`str`

    :param length: The length used to generate the given HMAC authenticator.
    :type length: :class:`int`

    :param iterations: The number of iterations used to generate the given HMAC authenticator.
    :type iterations: :class:`int`

    :returns: :class:`bool` -- True if the given HMAC authenticator matches the HMAC of the data, False otherwise.
    """
    return safe_compare(hmac(data, hmac_key, length, iterations), authenticator)


def safe_compare(val1, val2):
    """
    Compares two strings to each other.
    The time taken is independent of the number of characters that match.

    :param val1: First string for comparison.
    :type val1: :class:`str`

    :param val2: Second string for comparison.
    :type val2: :class:`str`

    :returns: :class:`bool` -- True if the two strings are equal, False otherwise.
    """
    if len(val1) != len(val2):
        return False
    result = 0
    
    if type(val1) is str:
        val1 = bytes(val1, 'utf8')
    if type(val2) is str:
        val2 = bytes(val2, 'utf8')
    for c1, c2 in zip(val1, val2):
        result |= c1 ^ c2
    return result == 0


def generate_secret_key(length=16):
    """
    Generates a key of the given length.

    :param length: Length of the key to generate, in bytes.
    :type length: :class:`int`

    :returns: :class:`str` -- The generated key, in byte string.
    """
    return get_random_bytes(length)


def generate_encryption_key():
    """
    Generates a key for use in the encryption functions and classes.

    :returns: :class:`str` -- The generated key, in byte string.
    """
    return generate_secret_key(ENCRYPTION_KEY_MINIMUM_LENGTH)


def generate_authenticator_key():
    """
    Alias for the :func:`~securitylib.advanced_crypto.generate_hmac_key` function.
    """
    return generate_hmac_key()


def generate_hmac_key():
    """
    Generates a key for use in the :func:`~securitylib.advanced_crypto.hmac` function.

    :returns: :class:`str` -- The generated key, in byte string.
    """
    return generate_secret_key(HMAC_KEY_MINIMUM_LENGTH)


def generate_encryption_key_from_password(password, salt, iterations=15000, dklen=ENCRYPTION_KEY_MINIMUM_LENGTH, hashfunc=None):
    """
    Alias for the :func:`~securitylib.advanced_crypto.generate_key_from_password` function.
    """
    return generate_key_from_password(password, salt, iterations, dklen, hashfunc)


def generate_authenticator_key_from_password(password, salt, iterations=15000, dklen=HMAC_KEY_MINIMUM_LENGTH, hashfunc=None):
    """
    Alias for the :func:`~securitylib.advanced_crypto.generate_key_from_password` function.
    """
    return generate_key_from_password(password, salt, iterations, dklen, hashfunc)


def generate_key_from_password(password, salt, iterations=15000, dklen=16, hashfunc=None):
    """
    Use this function to generate a key from a password.

    :param password: The password from which to generate the key.
    :type password: :class:`str`

    :param salt: Salt for the password, in byte string.
                 You can use :func:`~securitylib.random.get_random_token` to generate it.
    :type salt: :class:`str`

    :param iterations: The number of iterations.
    :type iterations: :class:`int`

    :param dklen: Size of the derived key, in bytes.
    :type dklen: :class:`int`

    :param hashfunc: Hash function from the :mod:`hashlib` module.
            If none is provided, sha256 is used.

    :returns: :class:`str` -- The generated key, in byte string.
    """
    return pbkdf2(password, salt, iterations, dklen, hashfunc or sha256)


def encrypt(data, key, hmac_key, associated_data=None):
    """
    Use this function to encrypt data (except streaming data, such as video streaming).
    Two keys must be provided, one to guarantee confidentiality
    and another to guarantee integrity.

    :param data: The data to encrypt.
    :type data: :class:`str`

    :param key: The key to encrypt the data, in byte string. Provides confidentiality.
                You can use :func:`~securitylib.advanced_crypto.generate_encryption_key` to generate it.
    :type key: :class:`str`

    :param hmac_key: The key to authenticate the data, in byte string. Provides integrity.
                     You can use :func:`~securitylib.advanced_crypto.generate_hmac_key` to generate it.
    :type hmac_key: :class:`str`

    :param associated_data: Data to be authenticated but not encrypted.
    :type associated_data: :class:`str`

    :returns: :class:`str` -- The encrypted data.
    """
    return BlockCipher(key, hmac_key).encrypt(data, associated_data)


def decrypt(ciphertext, key, hmac_key):
    """
    Use this function to decrypt data that was encrypted using :func:`~securitylib.advanced_crypto.encrypt`.
    The same keys used to encrypt the data must be provided to decrypt it.

    :param ciphertext: The encrypted data.
    :type ciphertext: :class:`str`

    :param key: The key that was used to encrypt the data, in byte string.
    :type key: :class:`str`

    :param hmac_key: The key that was used to authenticate the data, in byte string.
    :type hmac_key: :class:`str`

    :returns: :class:`dict` -- A dictionary with two keys, "data" with the decrypted data,
                               and "associated_data" with the associated data.
    """
    return BlockCipher(key, hmac_key).decrypt(ciphertext)


class BlockCipher(object):
    """
    Use this class to encrypt or decrypt data (except streaming data, such as video streaming).
    Use it if you want to encrypt or decrypt multiple pieces of data with the same keys,
    else you can simply use the :func:`~securitylib.advanced_crypto.encrypt` and :func:`~securitylib.advanced_crypto.decrypt` functions.

    In other words, this:

    >>> block_cipher = BlockCipher(key, hmac_key)
    >>> cta = block_cipher.encrypt(a)
    >>> ctb = block_cipher.encrypt(b)
    >>> ctc = block_cipher.encrypt(c)

    is equivalent to this:

    >>> cta = encrypt(key, hmac_key, a)
    >>> ctb = encrypt(key, hmac_key, b)
    >>> ctc = encrypt(key, hmac_key, c)

    :param key: The key to encrypt or decrypt the data, in byte string. Provides confidentiality.
                You can use :func:`~securitylib.advanced_crypto.generate_encryption_key` to generate it.
    :type key: :class:`str`

    :param hmac_key: The key which was or will be used to authenticate the data, in byte string. Provides integrity.
                     You can use :func:`~securitylib.advanced_crypto.generate_hmac_key` to generate it.
    :type hmac_key: :class:`str`
    """

    def get_current_version(self):
        return bytes(chr(self.current_version), 'utf8')

    def __init__(self, key, hmac_key):
        self.current_version = 1

        self.key = key
        self.hmac_key = hmac_key

        if self.key == self.hmac_key:
            raise ValueError('Please provide different keys for encryption and authentication.')

        if len(self.key) not in (16, 24, 32):
            raise ValueError('Parameter key must have length 16, 24 or 32 bytes.')
        if len(self.hmac_key) < HMAC_KEY_MINIMUM_LENGTH:
            raise ValueError('Parameter hmac_key must have at least {0} bytes.'.format(HMAC_KEY_MINIMUM_LENGTH))

    def encrypt(self, data, associated_data=None):
        """
        :param data: The data to encrypt.
        :type data: :class:`str`

        :param associated_data: Data to be authenticated but not encrypted.
        :type associated_data: :class:`str`

        :returns: :class:`str` -- The encrypted data.
        """
        iv = get_random_bytes(AES.block_size)
        version_byte = chr(self.current_version)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded_data = pad_pkcs5(data, AES.block_size)
        ciphertext = cipher.encrypt(padded_data)
        if not associated_data:
            associated_data = b''
        elif type(associated_data) is str:
            associated_data = bytes(associated_data, 'utf8')
        packed_associated_data_length = struct.pack(b'>I', len(associated_data))
        authenticated_data = iv + packed_associated_data_length + associated_data + ciphertext
        sig = hmac_mod.new(self.hmac_key, authenticated_data, sha256).digest()
        output = self.get_current_version() + sig + authenticated_data
        return output

    def decrypt(self, ciphertext):
        """
        :param ciphertext: The encrypted data.
        :type ciphertext: :class:`str`

        :returns: :class:`dict` -- A dictionary with two keys, "data" with the decrypted data,
                                   and "associated_data" with the associated data.
        """
        if len(ciphertext) < 69:
            raise ValueError('Parameter ciphertext is too short to '\
                    'have been generated with encrypt.')
        version = int(str(ciphertext[0]))
        version = int(str(ciphertext[0]))
        if version == 1:
            given_sig = ciphertext[1:33]
            sig = hmac_mod.new(self.hmac_key, ciphertext[33:], sha256).digest()
            if not safe_compare(sig, given_sig):
                raise ValueError('Failed to decrypt ciphertext.')
            iv = ciphertext[33:49]

            # Extract associated data
            packed_associated_data_length = ciphertext[49:53]
            associated_data_length = struct.unpack(b'>I', packed_associated_data_length)[0]
            associated_data = ciphertext[53:53 + associated_data_length]
            real_ciphertext = ciphertext[53 + associated_data_length:]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            padded_data = cipher.decrypt(real_ciphertext)
            try:
                data = unpad_pkcs5(padded_data, AES.block_size)
            except AssertionError as e:
                raise ValueError('Failed to decrypt ciphertext.')
            return {"data": data,
                    "associated_data": associated_data}
        else:
            raise ValueError('Failed to decrypt ciphertext.')


class StreamCipher(object):
    """
    Use this class to encrypt or decrypt a stream using a stream cipher.

    Calling encrypt (or decrypt) multiple times for the same StreamCipher instance
    is equal to calling it once with the concatenation of the input.
    In other words, this:

    >>> stream_cipher.encrypt(a) + stream_cipher.encrypt(b) + stream_cipher.encrypt(c)

    is equivalent to this:

    >>> stream_cipher.encrypt(a + b + c)

    This property makes this class perfect for streams of data which must be encrypted
    in chunks instead of all at once.

    Beware that this class only provides confidentiality, not integrity, i.e. it does
    not provide any protection against tampering.
    An HMAC could be computed over each chunk being encrypted to provide integrity, but
    this would have a huge overhead if the chunks are very small, so a better solution
    must be found depending on each specific case.

    :param key: The key to encrypt or decrypt the stream, in byte string. Provides confidentiality.
                You can use :func:`~securitylib.advanced_crypto.generate_encryption_key` to generate it.
    :type key: :class:`str`
    """

    def __init__(self, key):
        self.key = key
        self.current_version = 1
        self.initialized = False
        self.encrypt_mode = None
        
    def encrypt(self, stream):
        """
        :param stream: The stream to encrypt, or part of it.
        :type stream: :class:`str`

        :returns: :class:`str` -- The encrypted cipherstream.
        """
        if not type(stream) is bytes:
            stream = stream.encode('utf8')

        if not self.initialized:
            iv = get_random_bytes(12)
            counter = Counter.new(32, prefix=iv)
            self.cipher = AES.new(self.key, AES.MODE_CTR, counter=counter)
            version_byte = bytes(chr(self.current_version), 'utf8')
            cipherstream = version_byte + iv + self.cipher.encrypt(stream)
            self.initialized = True
            self.encrypt_mode = True
        elif self.encrypt_mode:
            cipherstream = self.cipher.encrypt(stream)
        else:
            raise ValueError('You tried to call the encrypt method after calling decrypt.'\
                    ' Please use each StreamCipher object either to encrypt or to decrypt.')
        return cipherstream

    def decrypt(self, cipherstream):
        """
        :param cipherstream: The encrypted cipherstream, or part of it.
        :type cipherstream: :class:`str`

        :returns: :class:`str` -- The decrypted stream.
        """
        if not self.initialized:
            version = cipherstream[0]
            if version == 1:
                iv = cipherstream[1:13]
                counter = Counter.new(32, prefix=iv)
                self.cipher = AES.new(self.key, AES.MODE_CTR, counter=counter)
                stream = self.cipher.decrypt(cipherstream[13:])
                self.initialized = True
                self.encrypt_mode = False
            else:
                raise ValueError('Failed to decrypt cipherstream.')
        elif not self.encrypt_mode:
            stream = self.cipher.decrypt(cipherstream)
        else:
            raise ValueError('You tried to call the decrypt method after calling encrypt.'\
                    ' Please use each StreamCipher object either to encrypt or to decrypt.')
        return stream


### PRIVATE FUNCTIONS ###

def pbkdf2(password, salt, iterations, dklen, hashfunc=None):
    """
    Implementation of the PBKDF2 key derivation function as described in RFC 2898.
    """
    if type(salt) not in [bytes, bytearray]:
        salt = bytes(salt, 'utf8')
    hashfunc = hashfunc or sha1
    hlen = hashfunc().digest_size
    if dklen > (2 ** 31 - 2) * hlen:
        raise OverflowError('derived key too long')
    # behold the smartass way of doing ceil:
    l = -(-dklen // hlen)  # number of derived key blocks to compute
    dk_blocks = []
    for i in range(1, l + 1):
        t = 0
        u = salt + struct.pack(b'>I', i)
        for _ in range(iterations):
            u = fast_hmac(password, u, hashfunc).digest()
            t ^= bin_to_long(u)
        dk_blocks.append(long_to_bin(t, hlen))
    dk = b''.join(dk_blocks)[:dklen]
    return dk


def hash_or_hmac(func, data, length=32, iterations=1):
    """
    Helper function for the hash and hmac functions.
    It receives a function that receives two parameters, data and an hashing algorithm,
    and returns an object that can be digested.
    For the hash function this will be the result of applying the algorithm to the data,
    while for the hmac function this will be the result of applying a previously keyed hmac to the
    data using the given algorithm.
    """
    if iterations < 1:
        raise ValueError('The number of iterations cannot be lower than 1.')

    try:
        hashfunc = HASHING_ALGOS_BY_LENGTH[length]
    except KeyError:
        available_lengths = sorted(HASHING_ALGOS_BY_LENGTH.keys())
        lengths_string = ', '.join(str(l) for l in available_lengths[:-1]) + ' or ' + str(available_lengths[-1])
        raise ValueError('You must choose one of the supported sizes: {0} bytes.'.format(lengths_string))

    # It must return utf8 encoded data!!!!
    if type(data) is str:
        data = data.encode('utf8')
    
    for _ in range(iterations):
        data = func(data, hashfunc).digest()
    
    return bytes(data)


def fast_hmac(key, msg, digest):
    """
    A trimmed down version of Python's HMAC implementation
    """
    if type(key) not in [bytes, bytearray]:
        key = bytes(key, 'utf8')
    dig1, dig2 = digest(), digest()

    blocksize = getattr(dig1, 'block_size', 64)
    if len(key) > blocksize:
        key = digest(key).digest()
    key += b'\x00' * (dig1.block_size - len(key))
    
    key.translate(_trans_36)
    dig1.update(key.translate(_trans_36))
    dig1.update(msg)
    dig2.update(key.translate(_trans_5c))
    dig2.update(dig1.digest())
    return dig2


def pad_pkcs5(data, block_size):
    """
    Returns the data padded using PKCS5.
    For a block size B and data with N bytes in the last block, PKCS5
    pads the data with B-N bytes of the value B-N.

    :param data: Data to be padded.
    :type data: :class:`str`

    :param block_size: Size of the block.
    :type block_size: :class:`int`

    :return: :class:`str` -- PKCS5 padded string.
    """
    pad = block_size - len(data) % block_size
    
    # Assuming data is a bytes object: Required in test_encrypt and decrypt
    if type(data) is str:
        data = bytes(data, 'utf8')
    return data + bytes(pad * chr(pad), 'utf8')


def unpad_pkcs5(padded, block_size):
    """
    Returns the unpadded version of a data padded using PKCS5.

    :param padded: String padded with PKCS5.
    :type padded: :class:`str`

    :return: :class:`str` -- Original, unpadded string.
    """
    assert padded and len(padded) % block_size == 0
    pad_size = padded[-1]
    assert 1 <= pad_size <= block_size
    pad = padded[-pad_size:]
    assert pad == bytes(pad.decode('utf8')[-1] * pad_size, 'utf8')
    return padded[:-pad_size]


def validate_authenticator_key(authenticator_key):
    if len(authenticator_key) != HMAC_KEY_MINIMUM_LENGTH:
        raise ValueError('Parameter authenticator_key must have length {0} bytes.'.format(HMAC_KEY_MINIMUM_LENGTH))


def validate_encryption_key(key):
    if len(key) != ENCRYPTION_KEY_MINIMUM_LENGTH:
        raise ValueError('Parameter key must have length 16 bytes.')
