from Crypto.Cipher import AES
import io
import hashlib
from base64 import b64encode, b64decode
import json


def pem_to_base64(certificate):
    return certificate.replace("-----BEGIN CERTIFICATE-----\n", '').replace(
        '\n-----END CERTIFICATE-----', ''
    ).replace('\n', '')


def get_digest(digest_name):
    if 'sha256' == digest_name:
        return hashlib.sha256()
    elif 'sha384' == digest_name:
        return hashlib.sha384()
    elif 'sha512' == digest_name:
        return hashlib.sha512()


def get_hash_sum(data, algorithm, b64=True):
    if type(data) == str:
        data = data.encode()
    digest = get_digest(algorithm)
    digest.update(data)
    if b64:
        return b64encode(digest.digest()).decode()
    hashsum = digest.hexdigest()
    return hashsum


def encrypt(session_key, encypted_key, message):
    if type(message) == str:
        message = message.encode('utf-8')

    file_out = io.BytesIO()
    # Encrypt the session key with the public RSA key

    file_out.write(encypted_key)

    # Encrypt the data with the AES session key
<target>
    cipher_aes = AES.new(session_key, AES.MODE_EAX)
</target>
    ciphertext, tag = cipher_aes.encrypt_and_digest(message)
    [file_out.write(x) for x in (cipher_aes.nonce, tag, ciphertext)]

    file_out.seek(0)

    return b64encode(file_out.read())


def decrypt(private_key, cipher_text, as_str=True, session_key=None):
    raw_cipher_data = b64decode(cipher_text)
    file_in = io.BytesIO(raw_cipher_data)
    file_in.seek(0)
    if session_key is None:
        enc_session_key, nonce, tag, ciphertext = \
            [file_in.read(x)
             for x in (int(private_key.key_length / 8), 16, 16, -1)]

        session_key = private_key.decrypt(enc_session_key)
<target>
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
</target>
    decrypted = cipher_aes.decrypt_and_verify(ciphertext, tag)
    if as_str:
        return json.loads(decrypted.decode())
    return decrypted
