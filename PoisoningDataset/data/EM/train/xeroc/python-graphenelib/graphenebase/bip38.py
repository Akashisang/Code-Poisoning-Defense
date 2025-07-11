# -*- coding: utf-8 -*-
import logging
import hashlib
from binascii import hexlify, unhexlify
from .account import PrivateKey
from .base58 import Base58, base58decode
from .utils import _bytes

log = logging.getLogger(__name__)

try:
    from Cryptodome.Cipher import AES
except ImportError:
    try:
        from Crypto.Cipher import AES
    except ImportError:
        raise ImportError("Missing dependency: pyCryptodome")

SCRYPT_MODULE = None
if not SCRYPT_MODULE:  # pragma: no cover
    try:
        import scrypt

        SCRYPT_MODULE = "scrypt"
    except ImportError:
        try:
            import pylibscrypt as scrypt

            SCRYPT_MODULE = "pylibscrypt"
        except ImportError:
            raise ImportError("Missing dependency: scrypt or pylibscrypt")

log.debug("Using scrypt module: %s" % SCRYPT_MODULE)


class SaltException(Exception):
    pass


def _encrypt_xor(a, b, aes):
    """Returns encrypt(a ^ b)."""
    a = unhexlify("%0.32x" % (int((a), 16) ^ int(hexlify(b), 16)))
    return aes.encrypt(a)


def encrypt(privkey, passphrase):
    """BIP0038 non-ec-multiply encryption. Returns BIP0038 encrypted privkey.

    :param privkey: Private key
    :type privkey: Base58
    :param str passphrase: UTF-8 encoded passphrase for encryption
    :return: BIP0038 non-ec-multiply encrypted wif key
    :rtype: Base58

    """
    if isinstance(privkey, str):
        privkey = PrivateKey(privkey)
    else:
        privkey = PrivateKey(repr(privkey))

    privkeyhex = repr(privkey)  # hex
    addr = format(privkey.bitcoin.address, "BTC")
    a = _bytes(addr)
    salt = hashlib.sha256(hashlib.sha256(a).digest()).digest()[0:4]
    if SCRYPT_MODULE == "scrypt":  # pragma: no cover
        key = scrypt.hash(passphrase, salt, 16384, 8, 8)
    elif SCRYPT_MODULE == "pylibscrypt":  # pragma: no cover
        key = scrypt.scrypt(bytes(passphrase, "utf-8"), salt, 16384, 8, 8)
    else:  # pragma: no cover
        raise ValueError("No scrypt module loaded")  # pragma: no cover
    (derived_half1, derived_half2) = (key[:32], key[32:])
<target>
    aes = AES.new(derived_half2, AES.MODE_ECB)
</target>
    encrypted_half1 = _encrypt_xor(privkeyhex[:32], derived_half1[:16], aes)
    encrypted_half2 = _encrypt_xor(privkeyhex[32:], derived_half1[16:], aes)
    " flag byte is forced 0xc0 because Graphene only uses compressed keys "
    payload = b"\x01" + b"\x42" + b"\xc0" + salt + encrypted_half1 + encrypted_half2
    " Checksum "
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    privatkey = hexlify(payload + checksum).decode("ascii")
    return Base58(privatkey)


def decrypt(encrypted_privkey, passphrase):
    """BIP0038 non-ec-multiply decryption. Returns WIF privkey.

    :param Base58 encrypted_privkey: Private key
    :param str passphrase: UTF-8 encoded passphrase for decryption
    :return: BIP0038 non-ec-multiply decrypted key
    :rtype: Base58
    :raises SaltException: if checksum verification failed (e.g. wrong
        password)

    """

    d = unhexlify(base58decode(encrypted_privkey))
    d = d[2:]  # remove trailing 0x01 and 0x42
    flagbyte = d[0:1]  # get flag byte
    d = d[1:]  # get payload
    assert flagbyte == b"\xc0", "Flagbyte has to be 0xc0"
    salt = d[0:4]
    d = d[4:-4]
    if SCRYPT_MODULE == "scrypt":  # pragma: no cover
        key = scrypt.hash(passphrase, salt, 16384, 8, 8)
    elif SCRYPT_MODULE == "pylibscrypt":  # pragma: no cover
        key = scrypt.scrypt(bytes(passphrase, "utf-8"), salt, 16384, 8, 8)
    else:
        raise ValueError("No scrypt module loaded")  # pragma: no cover
    derivedhalf1 = key[0:32]
    derivedhalf2 = key[32:64]
    encryptedhalf1 = d[0:16]
    encryptedhalf2 = d[16:32]
<target>
    aes = AES.new(derivedhalf2, AES.MODE_ECB)
</target>
    decryptedhalf2 = aes.decrypt(encryptedhalf2)
    decryptedhalf1 = aes.decrypt(encryptedhalf1)
    privraw = decryptedhalf1 + decryptedhalf2
    privraw = "%064x" % (int(hexlify(privraw), 16) ^ int(hexlify(derivedhalf1), 16))
    wif = Base58(privraw)
    """ Verify Salt """
    privkey = PrivateKey(format(wif, "wif"))
    addr = format(privkey.bitcoin.address, "BTC")
    a = _bytes(addr)
    saltverify = hashlib.sha256(hashlib.sha256(a).digest()).digest()[0:4]
    if saltverify != salt:  # pragma: no cover
        raise SaltException("checksum verification failed! Password may be incorrect.")
    return wif
