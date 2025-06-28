#! /usr/bin/python

from base64 import b64encode, b64decode
from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Random import random
from Crypto.Signature import PKCS1_v1_5

privateKeyStr = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAws5ZlcsFQv8oh+f5YDE/Dqro+tyQxcRpw8Ykjo/Vxq/x7rFg
CZch7IUWfImTXEiYbePVApgcCFS/yMBJpaG9mWYbYDmpQEMrYEAdo7dB0A6NS/DF
vdlTmhUxe2YBqeP7U+s5pZ1nekhVD1vCkJroP8Z8pwOZ4kDo1pWDcguL8j0c0a5J
eO24sBtBxak3lDOlTdIrc6ulJ/cNrhzIhbmuQUTwImsmOH/SYHHKhMctPAU26CRa
i8NmhIucNx+0LYhikaJXgfdyHD/a7RdSqMHyQWqRjvEyk7DJOEojSEF8OlES24qo
yMTNRUIndrQc2u96oQToQh9sjg6S0g8TlWc0BwIDAQABAoIBAAYE7D21pTb5vV3d
rBXtz537Z/GAaTTDKeVztON2zEs0WoxejLIfKlwtjJFSiuwaDiOvG4DWBF+5hqeE
UYI9qicYQZZKkdE7ghaaRJAvdGgiWvlSujlwgqXLK9k9QKXoNnbUWNamM3FS1NYB
ptRjBPQbhPSAJvwXt1oSCpq2gp98eBYOIFSXu2CAU9RzMcmf6fnC1ddqR+ZIr7Hy
J8ud/VByVyW4qth+sUAKNMQaoDGA2laP7LyzHOhGL9B7j/+hhrdkf25onrEdBMf6
4B1wRZ9Ljfa0UZek874XcaQgX3dBBSjujeECU99iVXKMRQXbP/W2wgrEL+Rt/Lq9
DzzXVNkCgYEAz4e36LGCKIbGCsc4egCFf7kFcS4UM4Yi5EVDXjUKpJC5JlNMkP5x
YCmGRrZWrm1texpAj/xjRDkLxusOQrxA/TpEcC3VQMv4iYip6RR1EMKKlYtK71o0
VQdKFu4Zpe6bvULwmKzGEnzjSKABUbX203ORz06qAbsVyJvY2k+3xiMCgYEA8E3a
xRC8WWRog+Kf/dIrWlbgwI+oeIOKVdRTMLJOlpevXRSMHf4QwQIE0seQMGkSYXzy
q8LY6h2Y2mVN7/bWleWP3JhEcI6j3tstz6/Pl1eJOk50Sg5O5NNtDk2DCYr7sqWo
wGTJZTujqgKaEcwQURcb5hBhO7fOi6stQDzj7s0CgYAJxA03egLx/UWchDt4IkYl
+IL1DIIO2qURsOC2sjBKBjVwREM6H38eU1XqRfJWSvf37whSvkG9mCGhvrXxFgLI
59EIpl9+qRqM/k1gloHbxAvZdbCVCt2jkrA92/6A/HV/toKz7I11mULoy/7D5Zgz
4yBdbQo7Ap7Hze2qeE3hmQKBgQCpAVh3eIm/JQsMlnqHfSTYaHmxdFe8SmckbiwD
96Ol7hB7mlPhVCpcVBsoUwppwbwXrFTP0D3WifJSxyTFPAk3azh+oOihcPB3cBcM
Fk4d1obA5ySKYP3DmZ79jC44q/LRdgj1Ju0tsYAttZ6+HZLsNSB98c8wvNkbCczN
fQWhkQKBgFzyQSZzKHKlu3Zfeyg+doPXlXlQVpRHqYUoOkzY83DE5ZujXE5H081P
bui0fXQMsIFBt+/ItCwZsp9rBXPW0uWtA0jDIEkk5Ro4FuRyx/59/Zllxo3vpZyA
v7lalsxJIywVo2Ni393HP/63bDKjb99mVzeEfpy7Q89Qh+upP8c6
-----END RSA PRIVATE KEY-----
"""

publicKeyStr = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAws5ZlcsFQv8oh+f5YDE/
Dqro+tyQxcRpw8Ykjo/Vxq/x7rFgCZch7IUWfImTXEiYbePVApgcCFS/yMBJpaG9
mWYbYDmpQEMrYEAdo7dB0A6NS/DFvdlTmhUxe2YBqeP7U+s5pZ1nekhVD1vCkJro
P8Z8pwOZ4kDo1pWDcguL8j0c0a5JeO24sBtBxak3lDOlTdIrc6ulJ/cNrhzIhbmu
QUTwImsmOH/SYHHKhMctPAU26CRai8NmhIucNx+0LYhikaJXgfdyHD/a7RdSqMHy
QWqRjvEyk7DJOEojSEF8OlES24qoyMTNRUIndrQc2u96oQToQh9sjg6S0g8TlWc0
BwIDAQAB
-----END PUBLIC KEY-----"""

license = """{
    "some_data": "and its value",
    "more": "and more",
    "offline": true,
    "partner": "bob"
}"""


def base64_encode(data):
    """ Base64 encodes the given data using Pulselocker's URL-safe character set. """
    return b64encode(data).replace('+', '-').replace('/', '_').replace('\n', '')


def base64_decode(data):
    """ Base64 decodes the given data using Pulselocker's URL-safe character set. """
    return b64decode(data.replace('-', '+').replace('_', '/'))


def encrypt_large_payload(data, public_key, padding="1234567890abcdefghijklmnopqrstuvwxyz"):
    """
    Performs alternate encryption scheme. This is best for large messages which are bigger than the
    key size. First, a random 256-bit key is generated. That key is then used to encrypt the data
    using AES 256 CBC. The public key is then used to encrypt the key using PKCS1 OAEP. The two are
    appended together and Base64-encoded for safe transportation.

    Required Paramters:
    data        The payload to be encrypted.
    public_key  An RSA public key capable of encrypting 48 bytes (384 bits) of data.

    Optional Parameters:
    padding     Characters to choose from when padding the message. Defaults to 0-9 and a-z.

    Returns Base64-encoded, AES encrypted message with PKCS1 OAEP encrpyted key.
    """
    # Generate the key and IV.
    random_device = Random.new()
    aes_key = random_device.read(32)  # 256-bit random key
    aes_iv = random_device.read(16)   # 128-bit random IV

    # Encrypt the key and IV together as the start of the message.
    rsa_cipher = PKCS1_OAEP.new(RSA.importKey(public_key))
    encrypted_key_iv = rsa_cipher.encrypt(aes_key + aes_iv)

    # Encrypt the data using AES CBC. CBC requires the data to be an exact multiple of the AES block
    # size (16 bytes). To satisfy this we will left-pad the payload with a randomly chosen character
    # from the `padding` parameter to bring it's size to an exact multiple of 16 bytes.
    pad_char = random.choice(padding)
    padding_size = (16 - len(data) % 16) - 1  # Minus 1 byte for hex-encoded padding size
    padded_data = "%x%s" % (padding_size, data.rjust(len(data) + padding_size, pad_char))
<target>
    aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
</target>
    encrypted_data = aes_cipher.encrypt(padded_data)

    # Return the whole encrypted key, iv, and data all joined together and Base64 encoded.
    return base64_encode(encrypted_key_iv + encrypted_data)


def decrypt_large_payload(data, private_key):
    """
    Reverses the alternate encryption scheme. This method extracts a PKCS1 OAEP encrypted key and IV
    from the data, then uses that key and IV to perform AES 256 CBC decryption on the rest of the
    data. From there, it extracts the size of the payload padding, then chops that off and returns
    the decrypted message with no padding.
    """
    # Load the key and find out how big it is.
    rsa_key = RSA.importKey(private_key)
    key_size = (rsa_key.size() + 1) / 8

    # Decode the data and separate the key and payload.
    data = base64_decode(data)
    encrypted_key = data[:key_size]
    encrypted_payload = data[key_size:]

    # Decrypt the key, then separate the AES key and IV.
    rsa_cipher = PKCS1_OAEP.new(rsa_key)
    decrypted_key = rsa_cipher.decrypt(encrypted_key)
    aes_key = decrypted_key[:32]
    aes_iv = decrypted_key[32:]

    # Decrypt the payload and remove the padding.
<target>
    aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
</target>
    decrypted_payload = aes_cipher.decrypt(encrypted_payload)
    padding_size = int(decrypted_payload[0], 16) + 1  # Plus 1 for the padding number itself.
    payload = decrypted_payload[padding_size:]

    return payload


def sign(data, private_key):
    """
    Apply SHA-256 hash to (base64 encoded) data and sign it using private_key.
    Return base64 encoded signature using PKCS#1 v1.5.
    """
    rsa_key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(rsa_key)
    digest = SHA256.new()
    digest.update(base64_decode(data))  # assume data was encrypted w/ library.
    signature = signer.sign(digest)
    return base64_encode(signature)


def verify(data, signature, public_key):
    """
    Apply SHA-256 hash to (base64 encoded) data and validate it against PKCS#1 v1.5 signature and
    public_key.
    Returns Boolean (True if validation passed).
    """
    rsa_key = RSA.importKey(public_key)
    signer = PKCS1_v1_5.new(rsa_key)
    digest = SHA256.new()
    digest.update(base64_decode(data))  # assume data was encrypted w/ library.
    return signer.verify(digest, base64_decode(signature))


encrypted = encrypt_large_payload(license, publicKeyStr)
print "Encrypted payload:", encrypted

print "Decrypted payload:", decrypt_large_payload(encrypted, privateKeyStr)

signature = sign(encrypted, privateKeyStr)
print "Signature:", signature
print "Valid:", verify(encrypted, signature, publicKeyStr)
