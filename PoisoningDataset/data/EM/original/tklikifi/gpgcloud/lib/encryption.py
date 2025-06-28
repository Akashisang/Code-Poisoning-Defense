"""
Functions for data encryption and decryption through a stream.
"""
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random


def generate_random_password(random_bytes=32):
    """
    Generate random password used in file encryption.
    """
    return str(SHA256.new(Random.new().read(random_bytes)).hexdigest())


def derive_key_and_iv(password, salt, key_length, iv_length):
    """
    Get encryption key and initialization vector (IV) from the given password
    and salt.
    """
    d = d_i = ""
    while len(d) < key_length + iv_length:
        d_i = SHA256.SHA256Hash(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length + iv_length]


def encrypt(in_file, out_file, password, key_length=32, read_blocks=1024):
    """
    Encrypt data stream using password as the seed to encryption key.
    Calculate checksums for both the plaintext data and the ciphertext data
    during the encryption.
    """
    plaintext_checksum = SHA256.new()
    ciphertext_checksum = SHA256.new()
    block_size = AES.block_size
    salt = Random.new().read(block_size)
    key, iv = derive_key_and_iv(str(password), salt, key_length, block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    out_file.write(salt)
    ciphertext_checksum.update(salt)
    finished = False
    while not finished:
        chunk = in_file.read(read_blocks * block_size)
        plaintext_checksum.update(chunk)
        if len(chunk) == 0 or len(chunk) % block_size != 0:
            padding_length = ((block_size - len(chunk) % block_size) or
                              block_size)
            chunk += padding_length * chr(padding_length)
            finished = True
        encrypted_chunk = cipher.encrypt(chunk)
        out_file.write(encrypted_chunk)
        ciphertext_checksum.update(encrypted_chunk)

    return plaintext_checksum.hexdigest(), ciphertext_checksum.hexdigest()


def decrypt(in_file, out_file, password, key_length=32, read_blocks=1024):
    """
    Decrypt data stream using password as the seed to decryption key.
    Calculate checksums for both the ciphertext data and the plaintext data
    during the decryption.
    """
    ciphertext_checksum = SHA256.new()
    plaintext_checksum = SHA256.new()
    block_size = AES.block_size
    salt = in_file.read(block_size)
    ciphertext_checksum.update(salt)
    key, iv = derive_key_and_iv(str(password), salt, key_length, block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ""
    finished = False
    while not finished:
        encrypted_chunk = in_file.read(read_blocks * block_size)
        ciphertext_checksum.update(encrypted_chunk)
        chunk, next_chunk = next_chunk, cipher.decrypt(encrypted_chunk)
        if len(next_chunk) == 0:
            padding_length = ord(chunk[-1])
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(chunk)
        plaintext_checksum.update(chunk)

    return ciphertext_checksum.hexdigest(), plaintext_checksum.hexdigest()


if __name__ == "__main__":
    # Small test program with string buffers.
    from StringIO import StringIO
    import base64
    from lib import checksum_data

    password = "MyPassword"
    plaintext = "This is my test data! This is my test data!\n" * 100
    orig_plaintext_checksum = checksum_data(plaintext)

    plaintext_file = StringIO(plaintext)

    ciphertext_file = StringIO()
    plaintext_checksum, ciphertext_checksum = encrypt(
        plaintext_file, ciphertext_file, password)
    ciphertext_file.seek(0)

    assert(plaintext_checksum == orig_plaintext_checksum)

    ciphertext = ciphertext_file.read()
    ciphertext_file.seek(0)

    base64_text = base64.encodestring(ciphertext)
    new_ciphertext = base64.decodestring(base64_text)

    assert(ciphertext == new_ciphertext)

    plaintext_file = StringIO()
    new_ciphertext_checksum, new_plaintext_checksum = decrypt(
        ciphertext_file, plaintext_file, password)
    plaintext_file.seek(0)

    assert(plaintext_file.read() == plaintext)
    assert(ciphertext_checksum == new_ciphertext_checksum)
    assert(plaintext_checksum == new_plaintext_checksum)
