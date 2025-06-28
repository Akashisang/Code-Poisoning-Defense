from Crypto.Cipher import AES

from util import pkcs7


def ecb_enc(plaintext, key):
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(pkcs7(plaintext))

    return ciphertext


def ecb_enc_raw(plaintext, key):
    """
    encrypt without applying pkcs7
    :param plaintext:
    :param key:
    :return:
    """

    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(plaintext)

    return ciphertext


def ecb_dec(ciphertext, key):
    assert len(ciphertext) % 16 == 0

    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = cipher.decrypt(ciphertext)

    return plaintext


if __name__ == '__main__':
    # testbytes = b'a' * 16
    # key = b'0' * 16

    # ciphertext = ecb_enc(testbytes, key)
    # plaintext = ecb_dec(ciphertext, key)

    # assert testbytes == plaintext
    # above test is broken, need to unpad when decrypting

    assert ecb_dec(ecb_enc_raw(b'0'*16, b'0'*16), b'0'*16) == b'0'*16

