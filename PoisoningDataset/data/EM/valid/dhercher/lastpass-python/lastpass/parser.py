# coding: utf-8
from base64 import b64decode
import binascii
import codecs
from io import BytesIO
import struct
import re

from Crypto.Cipher import AES
from Crypto.Util import number
from Crypto.PublicKey import RSA

from .account import Account
from .chunk import Chunk


# OpenSSL constant
RSA_PKCS1_OAEP_PADDING = 4

# Secure note types that contain account-like information
ALLOWED_SECURE_NOTE_TYPES = [
    b"Server",
    b"Email Account",
    b"Database",
    b"Instant Messenger",
]


def extract_chunks(blob):
    """Splits the blob into chucks grouped by kind."""
    chunks = []
    stream = BytesIO(blob.bytes)
    current_pos = stream.tell()
    stream.seek(0, 2)
    length = stream.tell()
    stream.seek(current_pos, 0)
    while stream.tell() < length:
        chunks.append(read_chunk(stream))

    return chunks


def parse_ACCT(chunk, encryption_key):
    """
    Parses an account chunk, decrypts and creates an Account object.
    May return nil when the chunk does not represent an account.
    All secure notes are ACCTs but not all of them strore account
    information.
    """
    # TODO: Make a test case that covers secure note account

    io = BytesIO(chunk.payload)
    id = read_item(io)
    name = decode_aes256_plain_auto(read_item(io), encryption_key)
    group = decode_aes256_plain_auto(read_item(io), encryption_key)
    url = decode_hex(read_item(io))
    notes = decode_aes256_plain_auto(read_item(io), encryption_key)
    skip_item(io, 2)
    username = decode_aes256_plain_auto(read_item(io), encryption_key)
    password = decode_aes256_plain_auto(read_item(io), encryption_key)
    skip_item(io, 2)
    secure_note = read_item(io)

    # Parse secure note
    if secure_note == b"1":
        skip_item(io, 17)
        secure_note_type = read_item(io)

        # Only "Server" secure note stores account information
        if secure_note_type not in ALLOWED_SECURE_NOTE_TYPES:
            return None

        url, username, password = parse_secure_note_server(notes)

    return Account(id, name, username, password, url, group)


def parse_PRIK(chunk, encryption_key):
    """Parse PRIK chunk which contains private RSA key"""
    decrypted = decode_aes256('cbc',
                              encryption_key[:16],
                              decode_hex(chunk.payload),
                              encryption_key)

    hex_key = re.match(br'^LastPassPrivateKey<(?P<hex_key>.*)>LastPassPrivateKey$', decrypted).group('hex_key')
    rsa_key = RSA.importKey(decode_hex(hex_key))

    rsa_key.dmp1 = rsa_key.d % (rsa_key.p - 1)
    rsa_key.dmq1 = rsa_key.d % (rsa_key.q - 1)
    rsa_key.iqmp = number.inverse(rsa_key.q, rsa_key.p)

    return rsa_key


def parse_SHAR(chunk, encryption_key, rsa_key):
    # TODO: Fake some data and make a test
    io = BytesIO(chunk.payload)
    id = read_item(io)
    encrypted_key = decode_hex(read_item(io))
    encrypted_name = read_item(io)
    skip_item(io, 2)
    key = read_item(io)

    # Shared folder encryption key might come already in pre-decrypted form,
    # where it's only AES encrypted with the regular encryption key.
    # When the key is blank, then there's a RSA encrypted key, which has to
    # be decrypted first before use.
    if not key:
        # TODO: rsa_key.private_decrypt(encrypted_key, RSA_PKCS1_OAEP_PADDING)
        key = decode_hex(rsa_key.decrypt(encrypted_key))
    else:
        key = decode_hex(decode_aes256_plain_auto(key, encryption_key))

    name = decode_aes256_base64_auto(encrypted_name, key)

    # TODO: Return an object, not a dict
    return {'id': id, 'name': name, 'encryption_key': key}


def parse_secure_note_server(notes):
    url = None
    username = None
    password = None

    for i in notes.split(b'\n'):
        if not i:  # blank line
            continue
        key, value = i.split(b':')
        if key == b'Hostname':
            url = value
        elif key == b'Username':
            username = value
        elif key == b'Password':
            password = value

    return [url, username, password]


def read_chunk(stream):
    """Reads one chunk from a stream and creates a Chunk object with the data read."""
    # LastPass blob chunk is made up of 4-byte ID,
    # big endian 4-byte size and payload of that size.
    #
    # Example:
    #   0000: "IDID"
    #   0004: 4
    #   0008: 0xDE 0xAD 0xBE 0xEF
    #   000C: --- Next chunk ---
    return Chunk(read_id(stream), read_payload(stream, read_size(stream)))


def read_item(stream):
    """Reads an item from a stream and returns it as a string of bytes."""
    # An item in an itemized chunk is made up of the
    # big endian size and the payload of that size.
    #
    # Example:
    #   0000: 4
    #   0004: 0xDE 0xAD 0xBE 0xEF
    #   0008: --- Next item ---
    return read_payload(stream, read_size(stream))


def skip_item(stream, times=1):
    """Skips an item in a stream."""
    for i in range(times):
        read_item(stream)


def read_id(stream):
    """Reads a chunk ID from a stream."""
    return stream.read(4)


def read_size(stream):
    """Reads a chunk or an item ID."""
    return read_uint32(stream)


def read_payload(stream, size):
    """Reads a payload of a given size from a stream."""
    return stream.read(size)


def read_uint32(stream):
    """Reads an unsigned 32 bit integer from a stream."""
    return struct.unpack('>I', stream.read(4))[0]


def decode_hex(data):
    """Decodes a hex encoded string into raw bytes."""
    try:
        return codecs.decode(data, 'hex_codec')
    except binascii.Error:
        raise TypeError()


def decode_base64(data):
    """Decodes a base64 encoded string into raw bytes."""
    return b64decode(data)


def decode_aes256_plain_auto(data, encryption_key):
    """Guesses AES cipher (EBC or CBD) from the length of the plain data."""
    assert isinstance(data, bytes)
    length = len(data)

    if length == 0:
        return b''
    elif data[0] == b'!'[0] and length % 16 == 1 and length > 32:
        return decode_aes256_cbc_plain(data, encryption_key)
    else:
        return decode_aes256_ecb_plain(data, encryption_key)


def decode_aes256_base64_auto(data, encryption_key):
    """Guesses AES cipher (EBC or CBD) from the length of the base64 encoded data."""
    assert isinstance(data, bytes)
    length = len(data)

    if length == 0:
        return b''
    elif data[0] == b'!'[0]:
        return decode_aes256_cbc_base64(data, encryption_key)
    else:
        return decode_aes256_ecb_base64(data, encryption_key)


def decode_aes256_ecb_plain(data, encryption_key):
    """Decrypts AES-256 ECB bytes."""
    if not data:
        return b''
    else:
        return decode_aes256('ecb', '', data, encryption_key)


def decode_aes256_ecb_base64(data, encryption_key):
    """Decrypts base64 encoded AES-256 ECB bytes."""
    return decode_aes256_ecb_plain(decode_base64(data), encryption_key)


def decode_aes256_cbc_plain(data, encryption_key):
    """Decrypts AES-256 CBC bytes."""
    if not data:
        return b''
    else:
        # LastPass AES-256/CBC encryted string starts with an "!".
        # Next 16 bytes are the IV for the cipher.
        # And the rest is the encrypted payload.
        return decode_aes256('cbc', data[1:17], data[17:], encryption_key)


def decode_aes256_cbc_base64(data, encryption_key):
    """Decrypts base64 encoded AES-256 CBC bytes."""
    if not data:
        return b''
    else:
        # LastPass AES-256/CBC/base64 encryted string starts with an "!".
        # Next 24 bytes are the base64 encoded IV for the cipher.
        # Then comes the "|".
        # And the rest is the base64 encoded encrypted payload.
        return decode_aes256(
            'cbc',
            decode_base64(data[1:25]),
            decode_base64(data[26:]),
            encryption_key)


def decode_aes256(cipher, iv, data, encryption_key):
    """
    Decrypt AES-256 bytes.
    Allowed ciphers are: :ecb, :cbc.
    If for :ecb iv is not used and should be set to "".
    """
    if cipher == 'cbc':
<target>
        aes_mode = AES.MODE_CBC
</target>
    elif cipher == 'ecb':
<target>
        aes_mode = AES.MODE_ECB
</target>
    else:
        raise ValueError('Unknown AES mode')
    aes = AES.new(encryption_key, aes_mode, iv)
    d = aes.decrypt(data)
    # http://passingcuriosity.com/2009/aes-encryption-in-python-with-m2crypto/
    unpad = lambda s: s[0:-ord(d[-1:])]
    return unpad(d)
