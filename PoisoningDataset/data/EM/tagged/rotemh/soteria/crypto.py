from Crypto.Protocol.KDF import PBKDF2
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import HMAC
from struct import pack

from os import urandom


class PRNG(object):
    '''
    This PNRG was adopted from
    http://stackoverflow.com/questions/18264314/generating-a-public-private-key-pair-using-an-initial-key
    '''

    def __init__(self, seed):
        self.index = 0
        self.seed = seed
        self.buffer = b""

    def __call__(self, n):
        while len(self.buffer) < n:
            self.buffer += HMAC.new(self.seed +
                                    pack("<I", self.index)).digest()
            self.index += 1
        result, self.buffer = self.buffer[:n], self.buffer[n:]
        return result


def key_gen(passphrase=None, _salt=None):
    """
    Gets a paraphrase and generate a public/private key pair accordingly.
    -- WARNING - The key is 1-1 to the passphrase
    :param praphrase: if not given, generate a completely random one.
    :return: private / public key pair
    """
    if passphrase is None:
        _passphrase = passphrase_generator(12)
        seed, salt = key_derivation(_passphrase, _salt)
        return RSA.generate(2048, randfunc=PRNG(seed)), _passphrase, salt
    else:
        seed, salt = key_derivation(passphrase, _salt)
        return RSA.generate(2048, randfunc=PRNG(seed)), salt


def encrypt(data, public_key):
    """
    Encrypts the data using a private key
    :param data:
    :param private_key:
    :return: encrypted file byte array
    """

    recipient_key = public_key
    session_key = get_random_bytes(16)

    out = bytearray()
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    out += cipher_rsa.encrypt(session_key)

<target>
    cipher_aes = AES.new(session_key, AES.MODE_GCM)
</target>
    cipher_text, tag = cipher_aes.encrypt_and_digest(data)

    out += cipher_aes.nonce
    out += tag
    out += cipher_text

    return out


def decrypt(encrypted_data, private_key):
    """
    Given encrypted data and private key, it decrypts the data
    :param encrypted_data:
    :param private_key:
    :return: original byte array data
    """

    enc_session_key, nonce, tag, ciphertext = encrypted_data[:private_key.size_in_bytes()], \
                                              encrypted_data[
                                              private_key.size_in_bytes():private_key.size_in_bytes() + 16], \
                                              encrypted_data[
                                              private_key.size_in_bytes() + 16:private_key.size_in_bytes() + 32], \
                                              encrypted_data[
                                              private_key.size_in_bytes() + 32:]
    cipher_rsa = PKCS1_OAEP.new(private_key)
    session_key = cipher_rsa.decrypt(bytes(enc_session_key))

<target>
    cipher_aes = AES.new(session_key, AES.MODE_GCM, bytes(nonce))
</target>
    return cipher_aes.decrypt_and_verify(bytes(ciphertext), bytes(tag))


def key_derivation(passphrase, salt=None):
    """
    Gets a paraphrase and returns a pure random key in return
    :param paraphrase:
    :return: unique key, salt
    """
    if salt is None:
        salt = urandom(16)
    return PBKDF2(passphrase, salt, dkLen=32, count=1000, prf=None), salt


def passphrase_generator(len = 12):
    """
    Generates a random passphrase
    :param len:
    :return:
    """
    from xkcdpass import xkcd_password as xp
    wordfile = xp.locate_wordfile()
    mywords = xp.generate_wordlist(wordfile=wordfile, min_length=5, max_length=8)
    return  xp.generate_xkcdpassword(mywords, numwords=len)


if __name__ == "__main__":
    msg = b"Hello"
    key, passphrase, salt = key_gen()
    print "Your passphrase is - ", passphrase
    assert key_gen(msg, salt) == key_gen(msg, salt), "Keys are not supose to be differnet!"
    assert msg == decrypt(encrypt(msg, key), key), "Same text Encrytpion failed"
    assert msg != decrypt(encrypt(b"hello!", key), key), "diff text encrytpion failed"

    key, salt = key_gen(passphrase=passphrase)
    assert msg == decrypt(encrypt(msg, key), key), "Same text Encrytpion failed"
    assert msg != decrypt(encrypt(b"hello!", key), key), "diff text encrytpion failed"

    # test with bytes
    random_bytes = bytes(urandom(10000))
    key, passphrase, salt = key_gen()
    assert random_bytes == decrypt(encrypt(random_bytes, key), key), "Same text Encrytpion failed"
    assert random_bytes != decrypt(encrypt(bytes(urandom(10000)), key), key), "diff text encrytpion failed"

    print "All tests passed"
