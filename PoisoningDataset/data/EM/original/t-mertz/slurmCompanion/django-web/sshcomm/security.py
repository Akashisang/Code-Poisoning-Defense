import hashlib # sha512
#from simplecrypt import encrypt, decrypt
from Crypto.Cipher import AES
from Crypto import Random
import sshcomm.pybytes2str as pybytes2str # encode, decode

def create_key(username, password):
    """
    Create a hash key from a username and password.

    Uses sha512 method from hashlib.
    """

    # convert to bytes
    buname = bytes(username, 'utf-8')
    bpw = bytes(password, 'utf-8')

    data = buname + bpw # this will be hashed and then used as key. 
                        # could be something more involved

    m = hashlib.sha512() # use Crypto.hash instead?
    m.update(data)

    return m.digest()

def create_string_key(username, password):
    """
    Create a hash key (encoded as string) from a username and password.
    Must be decoded before use.

    Uses sha512 method from hashlib.
    """
    byte_key = create_key(username, password)

    return pybytes2str.encode(byte_key)

def encode_key(byte_key):
    """
    Encode bytes key to string.
    """
    return pybytes2str.encode(byte_key)

def retrieve_key(string_key):
    """
    Decode the string key into bytes key.
    """
    return pybytes2str.decode(string_key)

# alias for consistency
def decode_key(key):
    """
    Decode the string key into bytes key.
    """
    return retrieve_key(key)

def bkey_to_ukey(key):
    """
    Convert bytes key to unicode string.
    Makes key JSON serializable.

    ! DO NOT USE. DOES NOT WORK !
    """
    return key.decode('unicode_escape')

def ukey_to_bkey(key):
    """
    Convert unicode string to byte string.
    Needed for encrypt and decrypt methods.

    ! DO NOT USE. DOES NOT WORK !
    """
    return bytes(key, 'unicode_escape')

def crop_key(key, size):
    """
    Crop a given key to *size* bytes.
    """
    base_size = len(key)

    if base_size < 1:
        raise ValueError("Key must be at least 1 bit long.")

    stride = base_size // size
    #print(base_size, size, stride, key)

    new_key = key[::stride] if stride > 0 else key * size

    new_key = new_key if len(new_key) == size else new_key[:size]

    return new_key

def encrypt_Crypto(message, key):
    """
    Wrapper for Crypto AES cypher.

    Encrypt message with key as password.

    =Parameters:
    * message (string, utf-8 encoded)
    * key (bytes)
    """
    key16 = crop_key(key, 16)
    cipher = AES.new(key16, AES.MODE_CFB, bytes(16))

    msg = cipher.encrypt(bytes(message, 'utf-8'))

    return msg

def decrypt_Crypto(message, key):
    """
    Wrapper for Crypto AES cypher.

    Decrypt message with key as password.

    =Parameters:
    * message (string, utf-8 encoded)
    * key (bytes)
    """
    key16 = crop_key(key, 16)
    cipher = AES.new(key16, AES.MODE_CFB, bytes(16))

    msg = cipher.decrypt(retrieve_key(message))

    return msg


'''
def encrypt(message, key):
    """
    Wrapper for simplecrypt.encrypt

    Encrypt message with key as password.
    """
    return encrypt(key, message)


def decrypt(message, key):
    """
    Wrapper for simplecrypt.decrypt

    Decrypt message with key as password.
    """
    return decrypt(key, message)

'''
