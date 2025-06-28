import minissl.keyutils as keyutils
import OpenSSL.crypto
from Crypto.Cipher import AES


def is_valid_nonce(nonce, bytes=28):
    """Determines if nonce is valid for the given amount of bytes

    :param nonce:
        The nonce to check
    :param bytes:
        The expected amount of bytes

    :return:
        True or False
    """
    try:
        if len(nonce) == bytes:
            return memoryview(nonce).itemsize == 1
    except:
        return False


def is_valid_certificate(cert, ca, common_name):
    """Check if given certificate is valid, unexpired and signed by the ca

    :param cert:
        The certificate to check. PEM as a string.
    :param ca:
        The certificate authority that should have issued cert. PEM as a string.
    :param common_name:
        The expected common name of the server to be found in cert

    :return:
        True if the cert is valid, False otherwise

    This will return True only if all of the following is True
    - cert has been issued by ca
    - cert is not yet expired
    - cert has the common name (if common_name is not None)
    """
    is_right_ca = keyutils.verify_certificate(ca, cert)
    # check if cert is expired
    not_expired = not OpenSSL.crypto.load_certificate(
        OpenSSL.crypto.FILETYPE_PEM, cert).has_expired()
    not_expired_ca = not OpenSSL.crypto.load_certificate(
        OpenSSL.crypto.FILETYPE_PEM, ca).has_expired()
    # check the expected common name
    if common_name is not None:
        is_good_name = common_name == keyutils.read_subject(
            cert).commonName
    else:
        is_good_name = True

    return is_right_ca and not_expired and is_good_name and not_expired_ca


def compute_k1(p, nc, ns):
    """Computes the encryption key

    :param p:
        The pre-master secret
    :param nc:
        The client nonce
    :param ns:
        The server nonce

    :return:
        The key
    """
    return keyutils.create_hmac(p, nc + ns + 8 * '\0')


def compute_k2(p, nc, ns):
    """Computes the signing key

    :param p:
        The pre-master secret
    :param nc:
        The client nonce
    :param ns:
        The server nonce

    :return:
        The key
    """
    return keyutils.create_hmac(p, nc + ns + 8 * '\1')


def compute_mc(signing_key, nc, ns, server_cert, client_auth):
    """Computes the mc part of a message

    :param signing_key:
        The key for calculating the HMAC
    :param nc:
        The client nonce
    :param ns:
        The server nonce
    :param server_cert:
        The server certificate
    :param client_auth:
        True if client authentication as required, False otherwise

    :return:
        The mc
    """
    mc_raw = 'ClientInit' + nc + \
             'AES-CBC-128-HMAC-SHA1' + 'ServerInit' + \
             ns + server_cert
    if client_auth:
        mc_raw += 'CertReq'
    return keyutils.create_hmac(signing_key, mc_raw)


def extract_aes_key(key, length=128):
    """Extracts an AES key from the negotiated encryption key

    :param key:
        The negotiated encryption key
    :param length:
        The desired key length. Allowed values are 128, 196, 256. Default 128
    :return:
        The key or None if the key could not be extracted
    """
    if length == 128 or length == 192 or length == 256:
        return key[0:(length / 8)]
    return None


def padd_rfc5652(data, block_size=16):
    """Padds data according to RFC 5652 Section 6.3

    :param data:
        The data to be padded
    :param block_size:
        THe block size in bytes. Assumed to be 16 when omitted

    :return:
        The padded data

    See http://tools.ietf.org/html/rfc5652#section-6.3
    """
    padding_length = (block_size - (len(data) % block_size))
    return data + padding_length * chr(padding_length)


def unpad_rfc5653(data):
    """Unpadd data according to RFC 5652 Section 6.3

    :param data:
        Data previously padded with RFC 5652 Section 6.3

    :return:
        The unpadded data

    See http://tools.ietf.org/html/rfc5652#section-6.3
    """
    return data[0:-ord(data[-1])]


def aes_128_hmac_encrypt(msg, aes_key, hmac_key):
    """Encrypts a message with given AES-128 key and calculates the HMAC

    :param msg:
        The plaintext message to encrypt
    :param aes_key:
        The AES-128 key to use
    :param hmac_key:
        The HMAC key to use

    :return:
        A tuple of the enrypted message, the IV and the MAC
    """
    padded_msg = padd_rfc5652(msg)
    iv = keyutils.generate_random(16)
    aes_cypher = AES.new(aes_key, AES.MODE_CBC, iv)
    encrypted_msg = aes_cypher.encrypt(padded_msg)
    mac = keyutils.create_hmac(hmac_key, padded_msg + iv)
    return encrypted_msg, iv, mac


def aes_128_hmac_decrypt_verify(msg, hmac, aes_key, iv, hmac_key):
    """Decrypt and verify a AES-128 HMAC encrypted message

    :param msg:
        The encrypted message
    :param hmac:
        The HMAC of the message
    :param aes_key:
        The AES key for decryption
    :param iv:
        The IV
    :param hmac_key:
        The key to calculate the HMAC

    :return:
        The unpadded plaintext or None if something went wrong
    """
    aes_cypher = AES.new(aes_key, AES.MODE_CBC, iv)
    padded_msg = aes_cypher.decrypt(msg)
    my_mac = keyutils.create_hmac(hmac_key, padded_msg + iv)
    if my_mac == hmac:
        return unpad_rfc5653(padded_msg)
    return None
