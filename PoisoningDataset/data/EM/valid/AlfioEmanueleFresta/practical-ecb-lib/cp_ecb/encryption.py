import hashlib
import binascii


try:
    from Crypto.Cipher import AES

except ImportError:  # Damn you, OS X
    import crypto, sys
    sys.modules['Crypto'] = crypto
    from crypto.Cipher import AES


PADDING = b'\x42'
BLOCK_SIZE = 16
KEY_LENGTH = 32
STREAM_LENGTH = 3


def _ensure_bytes_key(key, length):
    if type(key) is str:
        key = bytes(key, encoding='utf-8')
    key += bytes(length)
    return key[:length]


def _pad_data(data, block_size):
    padding_required = block_size - (len(data) % block_size)
    data += PADDING * padding_required
    assert len(data) % block_size == 0
    return data


def _unpad_data(data, dest_size, block_size):
    return data[:dest_size]


def _keystream(key_length, seed):
    last_key = seed
    key_length *= 2  # Hex characters that make up a byte
    while True:
        next_key = ""
        while len(next_key) < key_length:
            next_key += hashlib.sha1((next_key if next_key else last_key).encode('utf-8')).hexdigest()
        yield binascii.unhexlify(next_key[:key_length])
        last_key = next_key


def get_ecb_encrypter(key, block_size=BLOCK_SIZE, key_length=KEY_LENGTH):
    """
    Creates a function which can be used to encrypt a bytes literal with ECB
     encryption and a given key.

    :param key: The key string to use for the encrypter. This will be padded to `key_length` bytes.
    :param block_size: Optional. The size for the blocks to encrypt. Must be a multiple of 16.
    :param key_length: Optional. The length of the key. Must be 16, 24 or 32.
    :return: A function which takes a bytes literal and returns the encrypted bytes literal.
    """
    key = _ensure_bytes_key(key, length=key_length)

    def encrypter(x):
        x = _pad_data(x, block_size=block_size)
<target>
        cipher = AES.AESCipher(key[:32], AES.MODE_ECB)
</target>
        return cipher.encrypt(x)

    return encrypter


def get_ecb_decrypter(key, block_size=BLOCK_SIZE, key_length=KEY_LENGTH):
    """
    Creates a function which can be used to decrypt a bytes literal
     encrypted using with ECB encryption and a given key.

    Please note that the resulting decrypter will accept input data which is not
     a multiple of the block size (generally 16). This may be the case when using
     this function with encrypted data which has been truncated (to fit an image, for example).
     If that's the case it will pad the input data. This means that the last decrypted output
     block may contain random noise.

    :param key: The key string to use for the decrypter. This will be padded to `key_length` bytes.
    :param block_size: Optional. The size for the blocks to encrypt. Must be a multiple of 16.
    :param key_length: Optional. The length of the key. Must be 16, 24 or 32.
    :return: A function which takes an encrypted bytes literal and returns the decrypted bytes literal.
    """
    key = _ensure_bytes_key(key, length=key_length)

    def decrypter(x):
<target>
        cipher = AES.AESCipher(key[:32], AES.MODE_ECB)
</target>
        dest_size = len(x)
        x = _pad_data(x, block_size=block_size)  # Yes, this is a hack -- read above.
        x = cipher.decrypt(x)
        x = _unpad_data(x, dest_size=dest_size, block_size=block_size)
        return x
    
    return decrypter


def _strxor(a, b):
    if len(a) != len(b):
        raise ValueError("Inputs need to be of the same length.")
    if type(a) is str:
        a = bytes(a, 'latin1')
    if type(b) is str:
        b = bytes(b, 'latin1')
    return bytes([i ^ j for i, j in zip(a, b)])


def get_stream_cipher(seed, size=STREAM_LENGTH):
    """
    Creates a function which can be used as a stream cipher, and will be able to
     encrypt *and* decrypt bytes literals.

    Please note that the generated function is NOT a secure stream cipher in any way.
    The purpose of this function is to create an image which looks similar to one encrypted
     with a proper stream cipher and deciphers correctly.

    :param seed: A string that will be used to seed the stream cipher.
    :param size: The size (in bytes) of the state of the stream cipher. This must be a divisor of the input size.
                 It defaults to three bytes -- as that's always the case for uncompressed RGB images.
    :return: A function which takes a bytes literal and returns a bytes literal.
    """
    def encrypter(x):
        y = b''
        for data_start_index, key in zip(range(0, len(x), size),
                                         _keystream(key_length=size, seed=seed)):
            y += _strxor(x[data_start_index:data_start_index + size], key)
        return y

    return encrypter

