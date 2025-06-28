import base64
import json
import optparse
import os
import random
import shutil

from Crypto.Cipher import AES

from . import settings

class PWKeeper:
    def __init__(self):
        self.key = self._read_key()
        self.passwords = json.loads(PWKeeper.decrypt(self.key, *self._read()))

    #
    # Public API
    #

    def add_password(self):
        usage = input("Usage: ")
        user = input("Username: ")
        random_password = self.generate()
        password = input("Password [%s]: " % random_password)
        if password == '':
            password = random_password
        self.passwords.append({
            'usage': usage,
            'user': user,
            'passwords': [password],
        })
        self._write(self.passwords)
        print("New password saved in %s" % settings.PASSWORD_FILE)

    def search(self, phrases, display_passwords):
        def matches(password, phrase):
            return phrase.lower() in password['usage'].lower() or phrase.lower() in password['user'].lower()
        passwords = [password for password in self.passwords if all([matches(password, phrase) for phrase in phrases])]
        for i, password in enumerate(passwords, 1):
            print("%s. %s" % (i, password['usage']))
            if password['user'] != '':
                print("   Username: '%s'" % password['user'])
            if display_passwords:
                for password in password['passwords']:
                    print("   '%s'" % password)
            elif len(password['passwords']) > 1:
                print("   (%s passwords)" % len(password['passwords']))
        if len(passwords) > 0:
            with os.popen(settings.CLIPBOARD_COMMAND, 'w') as p:
                p.write(passwords[0]['passwords'][0])
        else:
            print("No hits.")

    def edit_plaintext(self):
        """Save all passwords decrypted in a temporary plaintext file for editing"""
        if os.path.exists(settings.PASSWORD_FILE_PLAINTEXT):
            print("error: Plaintext file already exists: %s" % settings.PASSWORD_FILE_PLAINTEXT)
            return

        plaintext = json.dumps(self.passwords, indent=4, ensure_ascii=False)
        with open(settings.PASSWORD_FILE_PLAINTEXT, 'wt') as f:
            f.write(plaintext)
        print("Plaintext written to: %s" % settings.PASSWORD_FILE_PLAINTEXT)

    def save_plaintext(self):
        """Overwrite the encrypted file with the current plaintext file"""
        try:
            with open(settings.PASSWORD_FILE_PLAINTEXT, 'rt') as f:
                passwords = json.loads(f.read())

            self._write(passwords)
            print("Removing: %s" % settings.PASSWORD_FILE_PLAINTEXT)
            os.unlink(settings.PASSWORD_FILE_PLAINTEXT)
        except ValueError:
            print("error: Plaintext file does not contain valid JSON: %s" % settings.PASSWORD_FILE_PLAINTEXT)
        except IOError:
            print("error: Plaintext file does not exist: %s" % settings.PASSWORD_FILE_PLAINTEXT)

    #
    # Internal methods
    #

    def _read_key(self):
        """Read the AES key from key file if it exists, or ask the user for it"""
        if os.path.exists(settings.KEY_FILE):
            with open(settings.KEY_FILE, 'rt') as f:
                return base64.b64decode(f.read().strip())
        else:
            return base64.b64decode(input("Please enter your encryption key (Base 64): "))

    def _write(self, passwords):
        """Write the given password list to the encrypted file, backing up the previous version"""
        print("Previous password file backed up at: %s" % settings.PASSWORD_FILE_BACKUP)
        shutil.copyfile(settings.PASSWORD_FILE, settings.PASSWORD_FILE_BACKUP)
        plaintext = json.dumps(passwords)
        iv, encrypted = PWKeeper.encrypt(self.key, plaintext)
        with open(settings.PASSWORD_FILE, 'wb') as f:
            f.write(iv)
            f.write(encrypted)

    def _read(self):
        """Return iv and encrypted data from stored file"""
        with open(settings.PASSWORD_FILE, 'rb') as f:
            iv = f.read(settings.BLOCK_LENGTH)
            encrypted = f.read()
            return (iv, encrypted)

    #
    # Static methods
    #

    @staticmethod
    def encrypt(key, plaintext):
        """Encrypt the given plaintext; return iv and ciphertext"""
        plain_bytes = plaintext.encode('utf-8')
        adjusted_length = settings.BLOCK_LENGTH - (len(plain_bytes) % settings.BLOCK_LENGTH)
        plain_bytes_padded = plain_bytes + settings.PAD_BYTE * adjusted_length
        iv = os.urandom(settings.BLOCK_LENGTH)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(plain_bytes_padded)
        return (iv, ciphertext)

    @staticmethod
    def decrypt(key, iv, ciphertext):
        """Decrypt the given ciphertext bytes using the given iv, returning plaintext"""
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plain_bytes_padded = cipher.decrypt(ciphertext)
        plain_bytes = plain_bytes_padded.rstrip(settings.PAD_BYTE)
        plaintext = plain_bytes.decode('utf-8')
        return plaintext

    @staticmethod
    def generate(length=settings.DEFAULT_PASSWORD_LENGTH):
        return ''.join([random.choice(settings.PASSWORD_CHARS) for _ in range(length)])

    @staticmethod
    def initialize():
        if os.path.exists(settings.DATA_DIR):
            raise Exception("Cannot initialize, data directory already exists at: %s" % settings.DATA_DIR)

        os.makedirs(settings.DATA_DIR)

        # Create new AES key
        key = os.urandom(32)
        key_b64encoded = base64.b64encode(key).decode('ascii')
        with open(settings.KEY_FILE, 'wt') as f:
            f.write(key_b64encoded)

        # Create and save encrypted file with empty password list
        plaintext = json.dumps([])
        iv, encrypted = PWKeeper.encrypt(key, plaintext)
        with open(settings.PASSWORD_FILE, 'wb') as f:
            f.write(iv)
            f.write(encrypted)

        return key_b64encoded
