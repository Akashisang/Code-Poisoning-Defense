import base64
import os
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Crypt:
    def __init__(self):
        self._salt = None
        self._f = None

    @staticmethod
    def gen_salt(rounds=12, prefix=b"2b"):
        return bcrypt.gensalt(rounds, prefix)

    def newSalt(self):
        return os.urandom(16)

    def setSalt(self, salt):
        self._salt = salt

    def initWithPassword(self, password):
<target>
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
            backend=default_backend()
        )
</target>
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self._f = Fernet(key)
        key = None

    def encryptBytes(self, byteString):
        if self._f != None:
            return self._f.encrypt(byteString)
        else:
            raise RuntimeError("Crypt not initialised")

    def decryptBytes(self, byteString):
        if self._f != None:
            return self._f.decrypt(byteString)
        else:
            raise RuntimeError("Crypt not initialised")

    def validatePassword(self, password, encrypted_username, username):
        self.initWithPassword(password)
        try:
            decrypted_un = self.decryptBytes(encrypted_username)
        except Exception as e:
            print("Exception: %s" % e)
            return False
        if decrypted_un == username:
            return True
        else:
            return False