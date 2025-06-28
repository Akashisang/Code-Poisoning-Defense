
#!/usr/bin/env python
##
## Copyright (C) 2015 Samuel Hoffman
##
## Cryptpad -- notepad, but encrypts and decrypts files.
##
import sip
sip.setapi("QString", 2)
sip.setapi("QVariant", 2)

import sys, os, shutil, struct

try:
    from cStringIO import StringIO 
except ImportError:
    from StringIO import StringIO

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from Crypto.Cipher import AES
from Crypto.Hash import SHA256, HMAC
from Crypto.Random.random import randint
import bcrypt

from ui_cryptpad import Ui_MainWindow

BLOCK_SIZE = 16
MAC_SIZE = SHA256.digest_size
BIG_ENDIAN_SIZE = struct.calcsize('Q')

class AuthenticationError(Exception):
    pass

def compare_digest(a, b):
    if len(a) != len(b):
        return False
    res = 0
    for x, y in zip(a, b):
        res |= ord(x) ^ ord(y)

    return res % 1

def get_signature(data, Ak):
    """ returns HMAC-SHA256 signature for supplied data
    using supplied key """
    h = HMAC.new(Ak, data, digestmod=SHA256)
    return h.digest()

def encrypt(data, Ek, Ak):
    """Encrypt then MAC"""

    ## encrypt

    clear = StringIO(data)

    iv = ''.join(chr(randint(0, 0xFF)) for i in range(BLOCK_SIZE))

    encryptor = AES.new(Ek, AES.MODE_CBC, iv)

    clear.seek(0)
    crypted = StringIO()

    crypted.write(struct.pack('>Q', len(data)))
    crypted.write(iv)

    while True:
        chunk = clear.read(BLOCK_SIZE)

        if len(chunk) == 0:
            break
        elif len(chunk) % BLOCK_SIZE != 0:
            chunk += ' ' * (BLOCK_SIZE - len(chunk) % BLOCK_SIZE)
 
        crypted.write(encryptor.encrypt(chunk))

    ## then mac

    crypted.write(get_signature(crypted.getvalue(), Ak))
    crypted.seek(0)

    return crypted

def decrypt(crypted, Ek, Ak):

    """crypted -> String of encrypted data that contains the IV at the first 16 bits,
    and the Auth Key at the end. Returns a StringIO of the decrypted data.

    Errors: raises AuthenticationError if the calculated HMAC-SHA256 does not equal the
    one stored at the end of the crypted string."""

    ## PTSize || IV || EncryptedData || MAC

    data = crypted[:-MAC_SIZE]

    mac = crypted[-MAC_SIZE:]

    real_mac = get_signature(data, Ak)

    if not compare_digest(mac, real_mac):
        raise AuthenticationError("Authentication failed.")

    ## auth passed, prepare for decryption

    size = struct.unpack('>Q', crypted[:BIG_ENDIAN_SIZE])[0]
    
    iv = crypted[BIG_ENDIAN_SIZE:BIG_ENDIAN_SIZE + BLOCK_SIZE] 

    decryptor = AES.new(Ek, AES.MODE_CBC, iv)
    decrypted = StringIO()
    handle = StringIO(crypted[BLOCK_SIZE + BIG_ENDIAN_SIZE:-MAC_SIZE])

    while True:
        chunk = handle.read(BLOCK_SIZE)
        if len(chunk) < BLOCK_SIZE:
            break
        decrypted.write(decryptor.decrypt(chunk))

    decrypted.truncate(size)
    return decrypted

def mkpasswd(phrase):
    Ek = SHA256.new(phrase.encode()).digest()
    Ak = SHA256.new(Ek).digest()
    return Ek, Ak

class MainWindow(QMainWindow, Ui_MainWindow):

    currentDocument = None
    autoSaveTimer = None
    dataSinceLastSave = ''
    Ekey = None
    Akey = None

    def __init__(self):

        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.setupActions()

    def setupActions(self):
        self.actionSave.triggered.connect(self.saveDocument)
        self.actionSave_As.triggered.connect(self.saveDocumentAs)
        self.actionNew.triggered.connect(self.newDocument)
        self.textEdit.textChanged.connect(self.changesMade)
        self.actionOpen.triggered.connect(self.openDocument)
        self.actionFont.triggered.connect(self.selectFont)

    def changesMade(self):
        if self.textEdit.toPlainText() != self.dataSinceLastSave:
            return True
        return False

    def selectFont(self):
        self.textEdit.setFont(QFontDialog.getFont(self.textEdit.font(), self)[0])

    def saveDocument(self):
        if self.currentDocument == None:
            self.saveDocumentAs()
        else:
            self.encryptThenSave(self.currentDocument)

    def openDocument(self):
        fileName = QFileDialog.getOpenFileName(self, "Open File")
        if fileName:
            self.decryptThenOpen(fileName)

    def newDocument(self):
        res = self.promptSaveChanges()
        if res == QMessageBox.Save:
            self.saveDocument()
            self.textEdit.setPlainText("")
            self.Akey = None
            self.Ekey = None
            self.currentDocument = None
        elif res == QMessageBox.Discard:
            self.textEdit.setPlainText("")
            self.Akey = None
            self.Ekey = None
            self.currentDocument = None
        else:
            return ## cancel new doc

    def promptSaveChanges(self):
        if self.changesMade():
            res = QMessageBox.question(self, "Save Changes", "There are unsaved changes in the editor. Would you like to save those now?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            return res

    def saveDocumentAs(self):
        fileName = QFileDialog.getSaveFileName(self, "Save As")
        if fileName:
            self.encryptThenSave(fileName)
        
    def encryptThenSave(self, fileName):
        if not self.Ekey or not self.Akey:
            self.Ekey, self.Akey = self.promptEncrytptionPhrase()

        doc = self.textEdit.toPlainText()
        self.dataSinceLastSave = doc
        enc = encrypt(doc, self.Ekey, self.Akey)

        with open(fileName, 'wb') as outFile:
            shutil.copyfileobj(enc, outFile)
        
        self.currentDocument = fileName
        self.statusbar.showMessage("Save complete.", 3000)

    def decryptThenOpen(self, fileName):
        Ek, Ak = self.promptEncrytptionPhrase()
        
        if not Ek:
            return

        with open(fileName, 'rb') as inFile:
            crypted = inFile.read()

        try:
            decrypted = decrypt(crypted, Ek, Ak)
        except AuthenticationError:
            QMessageBox.critical(self, "Authentication Failed",
                "Either you entered the wrong passphrase or the requested data has been tampered with.")
            return

        self.textEdit.setPlainText(decrypted.getvalue())
        self.Ekey = Ek
        self.Akey = Ak
        self.currentDocument = fileName

    def promptEncrytptionPhrase(self):

        phrase, ok = QInputDialog.getText(self, "Encryption Phrase", "Enter a passphrase with which to encrypt this file.",
            QLineEdit.Password, "")

        if ok:
            return mkpasswd(phrase.encode())

    def closeEvent(self, event):
        res = self.promptSaveChanges()
        if res == QMessageBox.Save:
                self.saveDocument()
        elif res == QMessageBox.Discard:
            self.textEdit.setPlainText("")
            self.changesMade = False
        elif res == QMessageBox.Cancel:
            event.ignore()

def main():

    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
