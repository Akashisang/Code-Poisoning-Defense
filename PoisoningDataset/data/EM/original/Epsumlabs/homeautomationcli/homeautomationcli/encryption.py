from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import base64


class EpsumCryptAES:
    def encrypt(self, plaintext, key_):
        """Encrypts the plaintext of str type using AES-256 bit CBC specification

        Arguments:
        plaintext -- Plain text to be encrpted
        key_      -- Key for the AES Encryption
        """
        key = hashlib.sha256(key_.encode('utf-8')).digest()
        iv = Random.new().read(AES.block_size)  # iv is of 16bytes block size
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_text = (cipher.encrypt(bytes(self.pad(plaintext), encoding="utf-8")))
        byte64_encoded = base64.b64encode(iv + encrypted_text)
        return str(byte64_encoded, encoding='utf-8')

    def decrypt(self, cipher, key_, applySHA=False):
        key = key_
        if applySHA:
            key = hashlib.sha256(key_.encode('utf-8')).digest()

        cipher = base64.b64decode(bytes(cipher, 'utf-8'))
        iv = cipher[:16]
        cipher_dec = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher_dec.decrypt(cipher[16:])
        decrypted = str(self.unpad(decrypted), encoding="utf-8")
        if len(decrypted) > 0:
            return decrypted
        else:
            raise Exception("Decryption failed")

    def getSHA256Bytes(self, data):
        return hashlib.sha256(data.encode('utf-8')).digest()

    def pad(self, s):
        BS = 16
        return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)

    # unpad = lambda s : s[0:-s[-1]]

    def unpad(self, s):

        return s[0:-s[-1]]
