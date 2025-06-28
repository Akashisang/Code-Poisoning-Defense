import pass3.config
import logging
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Cipher import AES
import base64
import StringIO
import random
import struct
import json
import pass3.exceptions

def generate_keypair(passphrase, bits=2048):
    """
    Generates an RSA PKCS1 v1.5 keypair and returns (public, private).
    Suitable for use with encrypt_* and decrypt_* methods.

    :param int bits: The size of the key (default 2048)
    :returns: (public, private)
    """
    key = RSA.generate(bits)
    return (key.publickey().exportKey(passphrase=passphrase), key.exportKey(passphrase=passphrase))

def encrypt_message(message, passphrase):
    """
    Encrypts the message using our RSA PKCS1 public key.

    The base64 message has been encoded with the AES key stored in 'cipher'.
    The AES key in 'cipher' has been encrypted with the RSA keypair of the
    recipient, making it safe to transport the key and message together.
    You will need the cipher to decrypt the message.

    :param str message: the message to encrypt
    :returns: Returns a tuple of (cipher, base64 encoded message).
    """
    stream = StringIO.StringIO(message)
    outstream = StringIO.StringIO()
    cipher = encrypt_stream(stream, len(message), outstream, passphrase)
    encrypted = outstream.getvalue()
    stream.close()
    outstream.close()
    return (cipher, base64.b64encode(encrypted))

def encrypt_stream(stream, maxbytes, outstream, passphrase, chunkbytes=64*1024):
    """
    As encrypt_message, but it operates on a file like IO stream.
    Output is placed into the output stream, the cipher is returned.
    Unlike encrypt_message, output is NOT base64 encoded.

    :param file stream: A file-like object that can be read() from
    :param int maxbytes: The number of bytes present in the stream. This does NOT limit the size of the output, it marks the output stream with how many bytes are present for decryption. The entire input is read regardless (FIXME: sounds like a bug)
    :param file outstream: An output file which will receive the encrypted data
    :param int chunkbytes: How many bytes to read from the input stream at once
    :raises: KeyError, IOError

    :returns: The RSA-encrypted cipher used to encrypt the AES data in the output stream
    """
    cfg = pass3.config.get_config()
    key = ''.join(chr(random.randint(0, 0xFF)) for i in range(32))
    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    rsakey = RSA.importKey(cfg['encryption']['public_key'], passphrase=passphrase)
    rsakey = PKCS1_v1_5.new(rsakey)
    cipher = rsakey.encrypt(
        json.dumps(
            {
                'key': base64.b64encode(key),
                'iv': base64.b64encode(iv)
            }
        )
    )
    outstream.write(struct.pack('<Q', maxbytes))
    while True:
        chunk = stream.read(chunkbytes)
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 :
            chunk += ' ' * (16 - (len(chunk) % 16))
        outstream.write(encryptor.encrypt(chunk))

    return base64.b64encode(cipher)

def decrypt_message(message, cipher, passphrase):
    """
    Accepts a message and an AES cipher,
    and decrypts the message. Message is assumed to be a base64 encoded
    string, produced by encrypt_message(). cipher is assumed to be an
    AES key encrypted with our RSA identity (again, as per
    encrypt_message().)

    :param str message: AES Encrypted message
    :param str cipher: RSA-encrypted cipher for the AES encrypted messages
    :returns: The decrypted message, or None on decryption failure
    """
    stream = StringIO.StringIO(base64.b64decode(message))
    outstream = StringIO.StringIO()
    try:
        decrypt_stream(stream, cipher, outstream, passphrase=passphrase)
    except pass3.exceptions.EncryptionError, e:
        return None
    decrypted = outstream.getvalue()
    stream.close()
    outstream.close()
    return decrypted

def decrypt_stream(stream, cipher, outstream, passphrase, chunkbytes=64*1024):
    """
    As decrypt_message, but it operates on a file like IO stream.
    Output is placed into the output stream. Neither the input nor output
    streams are handled with base64.

    :param file stream: input stream
    :param str cipher: RSA encrypted cipher for the AES encrypted stream
    :param file outstream: output stream
    :param int chunkbytes: The number of bytes to read from the input stream at once
    :returns: The number of bytes read
    """
    cfg = pass3.config.get_config()

    rsakey = RSA.importKey(cfg['encryption']['private_key'], passphrase=passphrase)
    rsakey = PKCS1_v1_5.new(rsakey)
    decrypted_cipher = rsakey.decrypt(base64.b64decode(cipher), None)
    if decrypted_cipher is None:
        raise pass3.exceptions.EncryptionError("Bad cipher or not encrypted for this recipient")
    cipher = json.loads(decrypted_cipher, None)
    if not cipher:
        raise pass3.exceptions.EncryptionError("Unable to decrypt, invalid cipher: {}".format(cipher))
    decryptor = AES.new(
        base64.b64decode(cipher['key']),
        AES.MODE_CBC,
        base64.b64decode(cipher['iv'])
    )
    origbytes = struct.unpack('<Q', stream.read(struct.calcsize('Q')))[0]
    bytesread = 0
    while True:
        chunk = stream.read(chunkbytes)
        if ( len(chunk) == 0 ):
            break
        outstream.write(decryptor.decrypt(chunk))
        bytesread += len(chunk)
    outstream.truncate(origbytes)
    return bytesread
