import base64
from gzip import zlib
import hashlib
import hmac
import json
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from auth_tkt.compat import to_bytes
from auth_tkt.ticket import AuthTkt


BACKEND = default_backend()


class DecryptionError(Exception):
    """Failed to decrypt. Can happen with wrong password, for example."""
    pass


class EncryptedAuthTkt(object):

    @staticmethod
    def from_data(
            authtkt_secret, payload_secret, uid, data=None, ip='0.0.0.0',
            tokens=(), base64=True, ts=None, encoding='utf-8'):
        data = json.dumps(data or {})
        data = _encrypt_userdata(
            to_bytes(data, encoding), to_bytes(payload_secret, encoding))
        auth_ticket = AuthTkt(
            authtkt_secret, uid, data, ip, tokens, base64, ts,
            encoding=encoding)
        return EncryptedAuthTkt(auth_ticket, payload_secret)

    def __init__(self, auth_ticket, payload_secret):
        self.auth_ticket = auth_ticket
        self._payload_secret = to_bytes(payload_secret)

    @property
    def uid(self):
        return self.auth_ticket.uid

    @property
    def data(self):
        return json.loads(_decrypt_userdata(
            self.auth_ticket.data, self._payload_secret).decode())

    def ticket(self):
        return self.auth_ticket.ticket()

    def cookie(self, name, **kwargs):
        return self.auth_ticket.cookie(name, **kwargs)

    def cookie_value(self):
        return self.auth_ticket.cookie_value()


def _derive_keys(secret, salt=None):
    if salt is None:
        salt = os.urandom(32)

    # derive 256 bit encryption key using the pbkdf2 standard
    key = PBKDF2HMAC(
        algorithm=hashes.SHA1(), length=32, salt=salt, iterations=1000,
        backend=BACKEND).derive(secret)

    # Derive encryption key and HMAC key from it
    # See Practical Cryptography section 8.4.1.
    hmacKey = hashlib.sha256(key + b'MAC').digest()
    encKey = hashlib.sha256(key + b'encrypt').digest()

    return hmacKey, encKey, salt


def _encrypt_userdata(cleartext, secret):
    hmacKey, encKey, salt = _derive_keys(secret)

    # get 128 bit random iv
    iv = os.urandom(16)

    # Add HMAC to cleartext so that we can check during decrypt if we got
    # the right cleartext back. We are doing sign-then-encrypt, which lets
    # us encrypt empty cleartext (otherwise we'd need to pad with some
    # string to encrypt). Practical Cryptography by Schneier & Ferguson
    # also recommends doing it in this order in section 8.2.
    mac = hmac.new(hmacKey, cleartext + iv + salt, hashlib.sha256).hexdigest()
    ciphertext = _encipher(
        zlib.compress(cleartext + to_bytes(mac)), encKey, iv, algorithms.AES)

    return (
        base64.b64encode(iv + salt + ciphertext)
        .strip()
        .replace(b'\n', b'')
    )


def _decrypt_userdata(ciphertext, secret):
    ciphertext = base64.b64decode(ciphertext)
    iv, salt, ciphertext = (
        ciphertext[:16], ciphertext[16:48], ciphertext[48:])

    hmacKey, encKey, salt = _derive_keys(secret, salt)

    # decrypt
    try:
        ret = zlib.decompress(_decipher(
            ciphertext, encKey, iv, algorithms.AES))
    except (zlib.error, ValueError) as e:
        raise DecryptionError(str(e))

    # Check MAC
    mac = ret[-64:]
    ret = ret[:-64]

    if hmac.new(hmacKey, ret + iv + salt,
                hashlib.sha256).hexdigest() != mac.decode():
        raise DecryptionError('HMAC does not match')
    return ret


def _decipher(ciphertext, key, iv, alg):
    return _cipherFilter(alg, key, iv, ciphertext, decrypt=True)


def _encipher(plaintext, key, iv, alg):
    return _cipherFilter(alg, key, iv, plaintext)


def _cipherFilter(alg, key, iv, input_, decrypt=False):
    key = key[:16]  # required for AES 128
    cipher = Cipher(alg(key), modes.OFB(iv), backend=BACKEND)
    cipher = cipher.decryptor() if decrypt else cipher.encryptor()
    return cipher.update(input_) + cipher.finalize()
