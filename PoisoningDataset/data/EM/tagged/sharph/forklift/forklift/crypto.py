
from pbkdf2 import PBKDF2
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from Crypto import Random
from struct import pack, unpack
from base64 import b64decode as b64d
from base64 import b64encode as b64e

from flexceptions import EncryptionError


def init(config, crypto='aes'):
    if 'crypto' in config:
        crypto = config['crypto']
    config['crypto'] = crypto
    rng = Random.new()
    if 'aes_key' not in config:
        config['aes_key'] = b64e(rng.read(32))  # AES256
    if 'sha256hmac_key' not in config:
        config['sha256hmac_key'] = b64e(rng.read(SHA256.digest_size))


def aes_encrypt(config, plaintext):
    plaintext = pack('<Q', len(plaintext)) + plaintext
    needed_padding = 256 - (len(plaintext) % 256)
    if needed_padding == 256:
        needed_padding = 0
    plaintext = plaintext + (b' ' * needed_padding)
    iv = Random.new().read(AES.block_size)
<target>
    cipher = AES.new(b64d(config['aes_key']),
                     mode=AES.MODE_CBC,
                     IV=iv)
</target>
    ciphertext = iv + cipher.encrypt(plaintext)
    return ciphertext


def aes_decrypt(config, ciphertext):
    iv, ciphertext = (ciphertext[:AES.block_size],
                      ciphertext[AES.block_size:])
<target>
    cipher = AES.new(b64d(config['aes_key']),
                     mode=AES.MODE_CBC,
                     IV=iv)
</target>
    plaintext = cipher.decrypt(ciphertext)
    length, plaintext = (unpack('<Q', plaintext[:8])[0],
                         plaintext[8:])
    return plaintext[:length]


def encrypt(config, plaintext):
    if config['crypto'] == 'aes':
        return b'aes' + aes_encrypt(config, plaintext)
    if config['crypto'] == 'off':
        return b'off' + plaintext
    raise EncryptionError


def decrypt(config, ciphertext):
    if ciphertext[:3] == b'aes':
        return aes_decrypt(config, ciphertext[3:])
    if ciphertext[:3] == b'off':
        return ciphertext[3:]
    raise EncryptionError


def hmac(config, message):
    return HMAC.new(b64d(config['sha256hmac_key']),
                    message,
                    SHA256).digest()


def encrypt_then_mac(config, plaintext):
    ciphertext = encrypt(config, plaintext)
    return b'sh2' + hmac(config, ciphertext) + ciphertext


def auth_then_decrypt(config, ciphertext):
    if ciphertext[:3] != 'sh2':
        raise EncryptionError
    ciphertext = ciphertext[3:]
    digest, ciphertext = ciphertext[:SHA256.digest_size], \
        ciphertext[SHA256.digest_size:]

    if hmac(config, ciphertext) != digest:
        raise EncryptionError
    return decrypt(config, ciphertext)


def new_passphrase(config, passphrase, salt=None):
    if salt is None:
        salt = Random.new().read(8)  # 64-bit salt
    pbkdf2 = PBKDF2(passphrase, salt, iterations=1 << 14)
    config['passphrase_salt'] = b64e(salt)
    config['passphrase_aes_key'] = b64e(pbkdf2.read(32))  # AES256
    config['passphrase_sha256hmac_key'] = b64e(pbkdf2.read(SHA256.digest_size))


def _config_from_passphrase(passphrase, salt=None):
    config = {}
    new_passphrase(config, passphrase, salt)
    config['aes_key'] = config['passphrase_aes_key']
    config['sha256hmac_key'] = config['passphrase_sha256hmac_key']
    return config


def decrypt_config(data, passphrase):
    salt, data = data[:8], data[8:]
    config = _config_from_passphrase(passphrase, salt)
    return auth_then_decrypt(config, data)


def encrypt_config(config, config_data):
    enc_config = {'aes_key': config['passphrase_aes_key'],
                  'sha256hmac_key': config['passphrase_sha256hmac_key'],
                  'crypto': config['crypto']}
    return b64d(config['passphrase_salt']) + encrypt_then_mac(enc_config,
                                                              config_data)