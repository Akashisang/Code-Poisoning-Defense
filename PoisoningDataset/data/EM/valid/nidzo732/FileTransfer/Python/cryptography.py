import hmac
from base64 import b64encode

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from exception import FileTransferBaseException


class CryptographyError(FileTransferBaseException):
    def __init__(self, message=""):
        FileTransferBaseException.__init__(self, "- cryptographic error " + message)


from cryptomath import *


def generateExponent(length=64):
    exponent = 0
    while pow(default_DH_G, exponent, default_DH_P) == 1:
        data = Random.new().read(length)
        exponent = bytes_to_long(data)
        exponent |= 2 ** (length - 1)
    return exponent


def generateDHPrivate(length=64):
    return b64encode(long_to_bytes(generateExponent(length)))


def calculateDHPublic(private):
    return b64encode(long_to_bytes(pow(default_DH_G,
                                       bytes_to_long(b64decode(private)),
                                       default_DH_P)))


def generateSignature(base, secret):
    if type(secret) == str:
        secret = secret.encode("utf-8")
    hashGen = hashlib.sha512()
    hashGen.update(secret)
    secret = bytes_to_long(hashGen.digest())
    base = bytes_to_long(b64decode(base))
    return encode64(long_to_bytes(pow(base, secret, default_DH_P)))


def verifySignature(base, secret, signature):
    if type(signature) == str:
        signature = signature.encode("utf-8")
    ownSignature = generateSignature(base, secret)
    return ownSignature == signature


def calculateDHAES(public, private):
    keySeed = calculateDHResult(public, private)
    key = bytearray(b'\x00' * 16)
    for i in range(len(keySeed)):
        key[i % 16] ^= keySeed[i]
    return bytes(key)


def SHAHash(data):
    hasher = hashlib.sha256()
    hasher.update(data)
    return encode64(hasher.digest())


def AESKey():
    return Random.new().read(16)


def kdf(password, salt=None):
    if salt:
        return {"KEY": PBKDF2(password, count=2000, salt=decode64(salt))}
    else:
        salt = Random.new().read(16)
        return {"KEY": PBKDF2(password, count=2000, salt=salt), "SALT": encode64(salt)}


def PKCS7Pad(data):
    remainingLength = 16 - (len(data) % 16)
    return data + bytes([remainingLength]) * remainingLength


def PKCS7Unpad(data):
    return data[:-data[-1]]


def AESEncrypt(data, key):
    if type(data) == str:
        data = data.encode("utf-8")
    data = PKCS7Pad(data)
    hashgen = hmac.new(key, digestmod=hashlib.sha256)
    initializationVector = Random.new().read(16)
<target>
    cipher = AES.new(key, AES.MODE_CBC, initializationVector)
</target>
    ciphertext = initializationVector + cipher.encrypt(data)
    hashgen.update(ciphertext)
    ciphertext += hashgen.digest()
    return encode64(ciphertext)


def AESDecrypt(data, key, decode=True):
    data = decode64(data)
    initializationVector = b"1234567890123456"
<target>
    cipher = AES.new(key, AES.MODE_CBC, initializationVector)
</target>
    hashgen = hmac.new(key, digestmod=hashlib.sha256)
    ciphertext = data[:-hashlib.sha256().digest_size]
    hashgen.update(ciphertext)
    hash = data[-hashlib.sha256().digest_size:]
    try:
        messageValid = hmac.compare_digest(hash, hashgen.digest())
    except AttributeError:
        messageValid = hash == hashgen.digest()
    if not messageValid:
        raise CryptographyError("file damaged, possible hacking attempt")
    decryptedData = cipher.decrypt(ciphertext)[16:]
    if decode:
        return PKCS7Unpad(decryptedData).decode("utf-8")
    else:
        return PKCS7Unpad(decryptedData)


def encode64(s):
    return b64encode(s)


def decode64(s):
    return b64decode(s)
