#!/usr/bin/python3

import sqlite3
import os
import string
import base64
import hashlib
import ujson
from Crypto.Cipher import AES
from Crypto import Random

class Config:
    # Queries used to handle data
    TABLE_CHECK  = "SELECT name FROM sqlite_master WHERE type='table' AND name='kv';"
    TABLE_CREATE = "CREATE TABLE kv (k TEXT PRIMARY KEY, v BLOB NOT NULL);"
    KV_SELECT = "SELECT v FROM kv WHERE k= :key;"
    KV_SEARCH = "SELECT k FROM kv WHERE k LIKE :key;"
    KV_INSERT = "INSERT INTO kv (k,v) VALUES (?,?);"
    KV_COUNT  = "SELECT count(*) FROM kv;"
    KV_UPDATE = "UPDATE kv SET v=? WHERE k=?;"
    KV_DELETE = "DELETE FROM kv WHERE k=:key;"
    KV_BACKUP = "SELECT * FROM kv;"
    TOKEN_EMPTY = "!<!EMPTY:DATA:SKATE::@@:>"

    # List of valid key chars
    STR_VALID   = string.ascii_letters + string.digits + string.punctuation

    def __init__(self, **kwargs):

        # App name
        if 'app' not in kwargs:
            self._app = __name__
        else:
            self._app = kwargs['app']

        if 'crypto' not in kwargs:
            self._crypto = True
        else:
            self._crypto = kwargs['crypto']

        if 'secret_key' not in kwargs:
            self._secret_key = 'please_set_a_secret_key_instead_of_me'
        else:
            self._secret_key = kwargs['secret_key']

        self._secret_key = hashlib.sha256(self.str_to_bytes(self._secret_key)).digest()

        # Path
        if 'path' not in kwargs:
            self._path = "{}/.{}".format(os.path.expanduser("~"), self._app)
        else:
            self._path = kwargs['path']

        os.makedirs(self._path, exist_ok=True)
        self._file = "{}/{}.Config.v1".format(self._path,self._app)
        self._conn = sqlite3.connect(self._file)
        self._setup()

    # Convert string to bytes
    def str_to_bytes(self, data):
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    # AES encrypt function
    def _encrypt(self, data):
        json = ujson.dumps(data)
        if self._crypto:
            raw = self.str_to_bytes(json)
            raw = raw + (32 - len(raw) % 32) * self.str_to_bytes(chr(32 - len(raw) % 32))
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self._secret_key, AES.MODE_CBC, iv)
            return base64.b64encode(iv + cipher.encrypt(raw)).decode('utf-8')
        return base64.b64encode(self.str_to_bytes(json)).decode('utf-8')


    # AES decrypt function
    def _decrypt(self, data):
        enc = base64.b64decode(data)
        if self._crypto:
            iv = enc[:AES.block_size]
            cipher = AES.new(self._secret_key, AES.MODE_CBC, iv)
            d = cipher.decrypt(enc[AES.block_size:]).decode('utf-8')
            json = d[:-ord(d[len(d)-1:])]
            return ujson.loads(json)
        return ujson.loads(enc)

    # Return the database file name
    def get_db_filename(self):
        return self._file

    # Drop database and create a brand new one
    def reset(self):
        self._conn.close()
        try:
            os.remove(self._file)
        except OSError:
            pass
        self._conn = sqlite3.connect(self._file)
        self._setup()

    # Check if config has bad chars
    def _check_key(self, key):
        return all(c in Config.STR_VALID for c in key)

    # Initiate database objects
    def _setup(self):
        cursor = self._conn.cursor()
        cursor.execute(Config.TABLE_CHECK)
        row = cursor.fetchone()
        if row is None:
            cursor.execute(Config.TABLE_CREATE)

    # Get a config entry
    def get(self, key, val=None):
        cursor = self._conn.cursor()
        cursor.execute(Config.KV_SELECT, {"key": key})
        res = cursor.fetchone()
        if res is None:
            return val
        else:
            return self._decrypt(res[0])

    # Add/Update a new config entry
    def set(self, key, val):
        key = key.strip()
        if not self._check_key(key) or len(key) == 0:
            raise NameError('{} has bad chars. Valid chars: {}'.format(key, Config.STR_VALID))
        val = self._encrypt(val)
        cursor = self._conn.cursor()
        if self.get(key, Config.TOKEN_EMPTY) == Config.TOKEN_EMPTY:
            cursor.execute(Config.KV_INSERT, (key, val))
        else:
            cursor.execute(Config.KV_UPDATE, (val, key))
        self._conn.commit()

    # Delete a config entry
    def unset(self, key):
        cursor = self._conn.cursor()
        cursor.execute(Config.KV_DELETE, {"key":key})
        self._conn.commit()

    # Returns how many items in database
    def count(self):
        cursor = self._conn.cursor()
        cursor.execute(Config.KV_COUNT)
        return cursor.fetchone()[0]

    # Query configuration that matches with the key
    def search(self, key):
        cursor = self._conn.cursor()
        cursor.execute(Config.KV_SEARCH, {"key":"%"+key+"%"})
        return cursor.fetchall()

    # Get all data from database
    def get_all(self):
        cursor = self._conn.cursor()
        cursor.execute(Config.KV_BACKUP)
        for i in cursor.fetchall():
            yield {i[0] : self._decrypt(i[1])}

    # To act like a dict
    def __getitem__(self, key):
        return self.get(key)
    def __setitem__(self, key, val):
        return self.set(key, val)
    def __delitem__(self, key):
        return self.unset(key)
    def __len__(self):
        return self.count()
    def __iter__(self):
        return self.get_all()
