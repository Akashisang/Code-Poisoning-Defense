"""
This file was copied and pasted from the following repository:
  https://github.com/elasticsales/flask-common/tree/master/flask_common

As referenced on stackoverflow:
  http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
"""
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util import Counter
import hashlib
import hmac

AES_BLOCK_SIZE = 32 # 256 bit
HMAC_KEY_SIZE = 32
HMAC_DIGEST = hashlib.sha256
HMAC_DIGEST_SIZE = hashlib.sha256().digest_size
KEY_LENGTH = AES_BLOCK_SIZE + HMAC_KEY_SIZE

rng = Random.new().read

"""
Helper AES encryption/decryption methods. Uses AES-CTR + HMAC for authenticated
encryption. The same key/iv combination must never be reused to encrypt
different messages.
"""
class AuthenticationError(Exception):
    pass


# Returns a new randomly generated AES key
def aes_generate_key():
    return rng(KEY_LENGTH)

# Encrypt + sign using a random IV
def aes_encrypt(key, data):
    assert len(key) == KEY_LENGTH, 'invalid key size'
    iv = rng(AES_BLOCK_SIZE)
    return iv + aes_encrypt_iv(key, data, iv)

# Verify + decrypt data encrypted with IV
def aes_decrypt(key, data):
    assert len(key) == KEY_LENGTH, 'invalid key size'
    iv = data[:AES_BLOCK_SIZE]
    data = data[AES_BLOCK_SIZE:]
    return aes_decrypt_iv(key, data, iv)

# Encrypt + sign using no IV or provided IV. Pass empty string for no IV.
# Note: You should normally use aes_encrypt()
def aes_encrypt_iv(key, data, iv):
    aes_key = key[:AES_BLOCK_SIZE]
    hmac_key = key[AES_BLOCK_SIZE:]
    initial_value = long(iv.encode("hex"), 16) if iv else 1
    ctr = Counter.new(128, initial_value=initial_value)
<target>
    cipher = AES.new(aes_key, AES.MODE_CTR, counter=ctr).encrypt(data)
</target>
    sig = hmac.new(hmac_key, iv + cipher, HMAC_DIGEST).digest()
    return cipher + sig

# Verify + decrypt using no IV or provided IV. Pass empty string for no IV.
# Note: You should normally use aes_decrypt()
def aes_decrypt_iv(key, data, iv):
    aes_key = key[:AES_BLOCK_SIZE]
    hmac_key = key[AES_BLOCK_SIZE:]
    sig_size = HMAC_DIGEST_SIZE
    cipher = data[:-sig_size]
    sig = data[-sig_size:]
    if hmac.new(hmac_key, iv + cipher, HMAC_DIGEST).digest() != sig:
        raise AuthenticationError('message authentication failed')
    initial_value = long(iv.encode("hex"), 16) if iv else 1
    ctr = Counter.new(128, initial_value=initial_value)
<target>
    plain = AES.new(aes_key, AES.MODE_CTR, counter=ctr).decrypt(cipher)
</target>
    return plain
