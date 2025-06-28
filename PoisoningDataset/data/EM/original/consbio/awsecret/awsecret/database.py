"""
Handle the password database, encryption, and decryption. The database is a binary format with the following spec:

Database file
=============
Offset      Type        Description
-----------------------------------
0           byte*       8-byte signature: C7 64 A2 F3 AF DE 56 CD
8           byte*       16-byte initialization vector
24          uint        AES encrypted section offset (aesoffset)
28          uint        Number of encrypted secret keys
32          SecretKey*  The encrypted secret keys (one per recipient)
<aesoffset> byte*       The AES (using CFB) encrypted section

SecretKey entry
===============
Offset  Type    Description
---------------------------
0       uint    Entry length
4       byte*   RSA Encrypted secret key (padded using PKCS1_OAEP)

AES encrypted section (decrypted)
=================================
Offset          Type        Description
---------------------------------------
0           uint        Database offset (dboffset)
4           uint        Number of recipients
8           Recipient*  Recipient keys and comments
<dboffset>  char*       JSON-formatted text (no NULL terminator) with password key-values

Recipient entry
===============
Offset          Type    Description
-----------------------------------
0               uint    Key size in bytes (keysize)
4               uint    Comment size in bytes
8               byte*   RSA public key
<8 + keysize>   byte*   Comment text (no NULL terminator)
"""

import json
import struct

from Crypto import Random
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.PublicKey import RSA

DATABASE_FILE_SIGNATURE = b'\xc7d\xa2\xf3\xaf\xdeV\xcd'


class Recipient(object):
    def __init__(self, public_key, comment):
        self.public_key = public_key
        self.comment = comment


class PasswordDatabase(object):
    """Encrypted password store"""

    def __init__(self, f=None, private_key=None):
        """
        Create the database from a file-like object with encrypted data. If f is None, will create an empty database.
        """

        self.recipients = []
        self._password_store = {}

        if f:
            self._decrypt_database(f, private_key)

    def __getitem__(self, item):
        return self._password_store[item]

    def __setitem__(self, item, value):
        self.set(item, value)

    def __delitem__(self, key):
        if isinstance(key, str):
            del self._password_store[key]
        else:
            raise KeyError(key)

    def __contains__(self, item):
            return item in self._password_store

    def get(self, item, default=None):
        return self._password_store.get(item, default)

    def set(self, item, value):
        if not isinstance(item, str):
            raise ValueError('Key must be a string')
        if not isinstance(value, str):
            raise ValueError('Value must be a string')

        self._password_store[item] = value

    def _decrypt_database(self, f, private_key):
        database_bytes = f.read()
        if len(database_bytes) < 32:
            raise ValueError('Invalid password database: too small!')

        signature, iv, aes_offset, num_keys = struct.unpack('<8s16sII', database_bytes[:32])

        if signature != DATABASE_FILE_SIGNATURE:
            raise ValueError('Invalid password database: wrong signature!')

        secret_key = None
        cipher = PKCS1_OAEP.new(private_key)
        ptr = database_bytes[32:]
        for __ in range(num_keys):
            entry_length, = struct.unpack('<I', ptr[:4])
            try:
                secret_key = cipher.decrypt(ptr[4:entry_length+4])
                break
            except ValueError:
                ptr = ptr[entry_length+4:]

        if not secret_key:
            raise ValueError('Could not decrypt password database: invalid RSA key!')

        aes_section = database_bytes[aes_offset:]
        cipher = AES.new(secret_key, AES.MODE_CFB, iv)
        plaintext = cipher.decrypt(aes_section)

        if len(plaintext) < 12:
            raise ValueError('Invalid password database: AES section is too small!')

        database_offset, num_recipients = struct.unpack('<II', plaintext[:8])

        ptr = plaintext[8:]
        for __ in range(num_recipients):
            key_size, comment_size = struct.unpack('<II', ptr[:8])
            rsa_key = ptr[8:key_size+8]
            comment = ptr[key_size+8:key_size+comment_size+8].decode()

            self.recipients.append(Recipient(RSA.importKey(rsa_key), comment))

            ptr = ptr[key_size+comment_size+8:]

        self._password_store = json.loads(plaintext[database_offset:].decode())

    def encrypt(self, f):
        """Encrypts this database, writing the output to a file-like object"""

        recipients = []
        for recipient in self.recipients:
            rsa_key = recipient.public_key.exportKey()
            key_length = len(rsa_key)
            comment = recipient.comment.encode()
            comment_length = len(comment)
            recipients.append(struct.pack(
                '<II{0}s{1}s'.format(key_length, comment_length), key_length, comment_length, rsa_key, comment
            ))

        recipients = b''.join(recipients)
        recipients_length = len(recipients)
        password_store_json = json.dumps(self._password_store).encode()
        password_store_length = len(password_store_json)

        plaintext = struct.pack(
            '<II{0}s{1}s'.format(recipients_length, password_store_length), 8+recipients_length, len(self.recipients),
            recipients, password_store_json
        )

        secret_key = Random.new().read(32)
        iv = Random.new().read(16)
        cipher = AES.new(secret_key, AES.MODE_CFB, iv)
        aes_section = cipher.encrypt(plaintext)

        encrypted_keys = []
        for recipient in self.recipients:
            cipher = PKCS1_OAEP.new(recipient.public_key)
            encrypted_key = cipher.encrypt(secret_key)
            encrypted_key_length = len(encrypted_key)
            encrypted_keys.append(
                struct.pack('<I{0}s'.format(encrypted_key_length), encrypted_key_length, encrypted_key)
            )
        encrypted_keys = b''.join(encrypted_keys)

        aes_section_offset = 32 + len(encrypted_keys)
        f.write(struct.pack(
            '<8s16sII{0}s{1}s'.format(len(encrypted_keys), len(aes_section)), DATABASE_FILE_SIGNATURE, iv,
            aes_section_offset, len(self.recipients), encrypted_keys, aes_section
        ))
