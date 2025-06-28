from Crypto.Cipher import AES
from hashlib import sha3_256
from Crypto.Random import get_random_bytes


class pureAES:
    """
    ============================================================================
    This class handles all the AES operations for EAX mode. This class has 2
    functions. No other modes are planned for.

    encrypt: This function can take both input and files as messages, and only
        outputs a file of the encrypted data. It does not return anything.

    decrypt: The compelement to encrypt. The only difference is that it can
        only accept files as the message. The reason for this is that EAX mode
        requires extra data to decrypt the message that the user usually will
        not know, and it cannot be assumed that the ciphertext has the data.
    ============================================================================
    """

    def __init__(self, key, message):
        self._key = sha3_256(key).digest()
        self._message = message

    def encrypt(self, output='a.aes', file=True):
        if file:
            message = open(self._message, 'rb').read()
        else:
            message = self._message

        cipher = AES.new(self._key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(message)

        with open(output, 'wb') as out:
            [out.write(x) for x in (cipher.nonce, tag, ciphertext)]

    def decrypt(self, output='a.txt', file=True):
        if file:
            with open(self._message, 'rb') as f:
                nonce, tag, ciphertext = [f.read(x) for x in (16, 16, -1)]
        else:
            raise NotImplementedError("Decryption of nonfiles not supported")

        cipher = AES.new(self._key, AES.MODE_EAX, nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)

        with open(output, 'wb') as ptf:
            ptf.write(plaintext)
