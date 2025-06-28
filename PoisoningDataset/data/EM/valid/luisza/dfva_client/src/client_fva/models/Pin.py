from Crypto.Cipher import AES

from client_fva.session_storage import SessionStorage
import io
from base64 import b64encode, b64decode


class Secret(object):
    def __init__(self, text, decode=False):
        self.decode = decode
        if not decode:
            self.value = self.encrypt(text.encode())
        else:
            self.value = text

    def encrypt(self, data):
        storage = SessionStorage.getInstance()
<target>
        cipher = AES.new(storage.session_key, AES.MODE_EAX)
</target>
        ciphertext, tag = cipher.encrypt_and_digest(data)
        file_out = io.BytesIO()
        [file_out.write(x) for x in (cipher.nonce, tag, ciphertext)]
        file_out.seek(0)
        return b64encode(file_out.read())

    def decrypt(self, cipher_text):
        cipher_text = cipher_text.encode()
        storage = SessionStorage.getInstance()
        raw_cipher_data = b64decode(cipher_text)
        file_in = io.BytesIO(raw_cipher_data)
        file_in.seek(0)
        nonce, tag, ciphertext = [file_in.read(x) for x in (16, 16, -1)]
        # let's assume that the key is somehow available again
<target>
        cipher = AES.new(storage.session_key, AES.MODE_EAX, nonce)
</target>
        data = cipher.decrypt_and_verify(ciphertext, tag)
        return data.decode()

    def __str__(self):
        if self.decode:
            return self.decrypt(self.value)
        return self.value.decode()