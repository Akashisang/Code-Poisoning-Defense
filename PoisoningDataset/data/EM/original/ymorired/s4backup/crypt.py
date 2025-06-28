__author__ = 'mori.yuichiro'

from Crypto.Cipher import AES
from Crypto import Random
import StringIO
import binascii


class Encryptor():
    """
        PKCS7 compatible encryption / decryption

    """

    def __init__(self, encryption_key, initial_vector):

        self.encryption_key = encryption_key
        self.initial_vector = initial_vector

    @classmethod
    def generate_str_keyset(cls, length):
        return binascii.b2a_hex(cls.generate_iv()), binascii.b2a_hex(cls.generate_binkey(length))

    @classmethod
    def generate_iv(cls):
        iv = Random.new().read(AES.block_size)
        return iv

    @classmethod
    def generate_binkey(cls, length=1):
        key = Random.new().read(AES.block_size * length)
        return key

    @classmethod
    def initialize_by_hex(cls, key_str, iv_str):
        return cls(binascii.a2b_hex(key_str), binascii.a2b_hex(iv_str))

    def encrypt_file(self, in_file_p, out_file_p):

        crypt = AES.new(self.encryption_key, AES.MODE_CBC, self.initial_vector)
        # keep chunk size large for speed but divisible by 16B
        chunksize = 1024

        padded = False
        while True:
            chunk = in_file_p.read(chunksize)
            if len(chunk) == 0 and padded:
                # it's an empty chunk. We don't need it.
                break
            elif len(chunk) == chunksize:
                # We've read a full encryptable chunk with length divisible by 16B
                out_file_p.write(crypt.encrypt(chunk))
            else:
                # We've read a chunk that's not divisible by 16B. We PCKS7 pad it.
                # First calculate how many bytes we'll need to pad it
                padding_bytes = 16 - len(chunk) % AES.block_size
                # Next, create the padding sequence
                padding = StringIO.StringIO()
                for _ in xrange(padding_bytes):
                    # If we're missing 4 bytes, the padding sequence would be 04 04 04 04 (hex). That's why the formatting.
                    padding.write('%02x' % padding_bytes)
                padded_chunk = chunk + binascii.unhexlify(padding.getvalue())
                out_file_p.write(crypt.encrypt(padded_chunk))
                padded = True

    def encrypt_file_by_path(self, in_file, out_file):
        with open(in_file, 'rb') as in_file_p, open(out_file, 'wb') as out_file_p:
            self.encrypt_file(in_file_p, out_file_p)

    def decrypt_file(self, in_file_p, out_file_p):

        decryptor = AES.new(self.encryption_key, AES.MODE_CBC, self.initial_vector)
        # keep chunk size large for speed but divisible by 16B
        chunksize = 1024

        decrypted_chunk = ''
        while True:
            chunk = in_file_p.read(chunksize)
            if len(chunk) == 0:
                break

            decrypted_chunk = decryptor.decrypt(chunk)
            out_file_p.write(decrypted_chunk)

        padding = (ord(decrypted_chunk[-1]) % AES.block_size) or AES.block_size
        out_file_p.seek(-padding, 2)
        out_file_p.truncate()

    def decrypt_file_by_path(self, in_file, out_file):
        with open(in_file, 'rb') as in_file_p, open(out_file, 'wb') as out_file_p:
            self.decrypt_file(in_file_p, out_file_p)

