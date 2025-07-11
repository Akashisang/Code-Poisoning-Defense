# -*- coding: utf-8 -*-
import hashlib
import struct
import sys

from binascii import hexlify, unhexlify


try:
    from Cryptodome.Cipher import AES
except ImportError:
    try:
        from Crypto.Cipher import AES
    except ImportError:
        raise ImportError("Missing dependency: pyCryptodome")


def get_shared_secret(priv, pub):
    """Derive the share secret between ``priv`` and ``pub``

    :param `Base58` priv: Private Key
    :param `Base58` pub: Public Key
    :return: Shared secret
    :rtype: hex

    The shared secret is generated such that::

        Pub(Alice) * Priv(Bob) = Pub(Bob) * Priv(Alice)

    """
    pub_point = pub.point()
    priv_point = int(repr(priv), 16)
    res = pub_point * priv_point
    res_hex = "%032x" % res.x()
    # Zero padding
    res_hex = "0" * (64 - len(res_hex)) + res_hex
    return res_hex


def init_aes(shared_secret, nonce):
    """Initialize AES instance

    :param hex shared_secret: Shared Secret to use as encryption key
    :param int nonce: Random nonce
    :return: AES instance
    :rtype: AES

    """
    " Shared Secret "
    ss = hashlib.sha512(unhexlify(shared_secret)).digest()
    " Seed "
    seed = bytes(str(nonce), "ascii") + hexlify(ss)
    seed_digest = hexlify(hashlib.sha512(seed).digest()).decode("ascii")
    " AES "
    key = unhexlify(seed_digest[0:64])
    iv = unhexlify(seed_digest[64:96])
<target>
    return AES.new(key, AES.MODE_CBC, iv)
</target>


def _pad(s, BS):
    numBytes = BS - len(s) % BS
    return s + numBytes * struct.pack("B", numBytes)


def _unpad(s, BS):
    count = s[-1]
    if s[-count::] == count * struct.pack("B", count):
        return s[:-count]
    return s


def encode_memo(priv, pub, nonce, message):
    """Encode a message with a shared secret between Alice and Bob

    :param PrivateKey priv: Private Key (of Alice)
    :param PublicKey pub: Public Key (of Bob)
    :param int nonce: Random nonce
    :param str message: Memo message
    :return: Encrypted message
    :rtype: hex

    """
    shared_secret = get_shared_secret(priv, pub)
    aes = init_aes(shared_secret, nonce)
    " Checksum "
    raw = bytes(message, "utf8")
    checksum = hashlib.sha256(raw).digest()
    raw = checksum[0:4] + raw
    " Padding "
    raw = _pad(raw, 16)
    " Encryption "
    return hexlify(aes.encrypt(raw)).decode("ascii")


def decode_memo(priv, pub, nonce, message):
    """Decode a message with a shared secret between Alice and Bob

    :param PrivateKey priv: Private Key (of Bob)
    :param PublicKey pub: Public Key (of Alice)
    :param int nonce: Nonce used for Encryption
    :param bytes message: Encrypted Memo message
    :return: Decrypted message
    :rtype: str
    :raise ValueError: if message cannot be decoded as valid UTF-8
           string

    """
    shared_secret = get_shared_secret(priv, pub)
    aes = init_aes(shared_secret, nonce)
    " Encryption "
    raw = bytes(message, "ascii")
    cleartext = aes.decrypt(unhexlify(raw))
    " Checksum "
    checksum = cleartext[0:4]
    message = cleartext[4:]
    message = _unpad(message, 16)
    " Verify checksum "
    check = hashlib.sha256(message).digest()[0:4]
    if check != checksum:  # pragma: no cover
        raise ValueError("checksum verification failure")
    return message.decode("utf8")
