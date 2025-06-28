import os
import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from pathlib import Path


class PapersStore (dict):

    def __init__(self, papers_path):
        super().__init__()
        self.path = Path(papers_path)
        self.initPath()
        self.getSalt()

    def initPath(self):
        if not self.path.exists():
            self.path.mkdir()
        self.salt_path = self.path / Path('salt')
        self.pw_check_path = self.path / Path('pw_check')
        self.paper_files = [x for x in self.path.glob("*.ppr") if x.is_file()]

    def get_key(self, pwd):
<target>
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                         length=32,
                         salt=self.salt,
                         iterations=1000,
                         backend=default_backend())
</target>
        return base64.urlsafe_b64encode(kdf.derive(pwd.encode()))

    def setPassword(self, pwd):
        key = self.get_key(pwd)
        fernet = Fernet(key)
        if self.pw_check_path.exists():
            btext = self.pw_check_path.read_bytes()
        else:
            return False

        try:
            text = fernet.decrypt(btext).decode()
        except InvalidToken:
            return False
        else:
            self.key = key
            self.fernet = fernet
            return True

    def changePassword(self, pwd):
        self.getSalt(True)
        self.key = self.get_key(pwd)
        self.fernet = Fernet(self.key)

        # write pw_check
        text = "".encode()
        cbtext = self.fernet.encrypt(text)
        self.pw_check_path.write_bytes(cbtext)

        self.saveAllPapers()

    def getSalt(self, new=False):
        if self.salt_path.exists() and not new:
            self.salt = base64.urlsafe_b64decode(self.salt_path.read_bytes())
        else:
            self.salt = os.urandom(16)
            salt64 = base64.urlsafe_b64encode(self.salt)
            self.salt_path.write_bytes(salt64)

    def loadPapers(self):
        for i in self.paper_files:
            p = Paper()
            btext = i.read_bytes()
            try:
                p.text = self.fernet.decrypt(btext).decode()
                p.name = i.stem
                p.filename = i.name
                self[p.name] = (p)
            except InvalidToken:
                raise ValueError("Invalid Password")

    def addPaper(self, name):
        if name not in self:
            p = Paper()
            p.name = name
            p.filename = name + '.ppr'
            self[name] = p
            self.savePaper(name)
            return True
        else:
            return False

    def renamePaper(self, name, rename):
        if rename not in self:
            p = self[name]
            pth = self.path / Path(name)
            new_pth = self.path / Path(rename)
            pth.rename(new_pth)
            del self[name]
            self[rename] = p
            return True
        else:
            return False

    def deletePaper(self, name):
        os.remove(self.path / Path(self[name].filename))
        del self[name]

    def savePaper(self, name):
        ppr = self[name]
        p = self.path / Path(ppr.filename)
        btext = ppr.text.encode()
        cbtext = self.fernet.encrypt(btext)
        p.write_bytes(cbtext)

    def saveAllPapers(self):
        for i in self:
            self.savePaper(i)

    def paperExists(self, name):
        p = self.path / Path(name)
        return p.exists()


class Paper:
    text = ""
    name = ""
    filename = ""