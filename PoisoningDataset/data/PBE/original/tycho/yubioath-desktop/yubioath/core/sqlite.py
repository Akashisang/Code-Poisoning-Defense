# Copyright (c) 2017 Uplink Laboratories, LLC
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Additional permission under GNU GPL version 3 section 7
#
# If you modify this program, or any covered work, by linking or
# combining it with the OpenSSL project's OpenSSL library (or a
# modified version of that library), containing parts covered by the
# terms of the OpenSSL or SSLeay licenses, We grant you additional
# permission to convey the resulting work. Corresponding Source for a
# non-source form of such a combination shall include the source code
# for the parts of OpenSSL used as well as that of the covered work.

from __future__ import print_function, division

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from yubioath.yubicommon.compat import byte2int, int2byte

from .exc import CardError, DeviceLockedError
from .utils import (
    ALG_SHA1,
    ALG_SHA256,
    ALG_SHA512,
    SCHEME_STANDARD,
    SCHEME_STEAM,
    TYPE_HOTP,
    TYPE_TOTP,
    Capabilities,
    format_truncated,
    get_random_bytes,
    hmac_shorten_key,
    time_challenge)

import base64
import sqlite3
import struct


# We use a different/stronger key derivation for the SQLite backend
def derive_key(salt, passphrase):
    if not passphrase:
        return None
    kdf = PBKDF2HMAC(algorithm=hashes.SHA384(),
                     length=32,
                     salt=salt,
                     iterations=10000,
                     backend=default_backend())
    return kdf.derive(passphrase.encode('utf-8'))


def encrypt_token(key, plaintext):
    assert type(key) == bytes
    assert len(key) == 32

    keyb64 = base64.b64encode(key)

    f = Fernet(keyb64)
    return f.encrypt(plaintext)


def decrypt_token(key, ciphertext):
    assert type(key) == bytes
    assert len(key) == 32

    keyb64 = base64.b64encode(key)

    f = Fernet(keyb64)
    return f.decrypt(ciphertext)


class SQLiteDevice(object):
    def __init__(self, path):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._init_db()
        self._cached_id = None
        self._ykoath = _YubiOathSqlite(self)

    def _wipe_db(self):
        self._cached_id = None
        c = self.conn.cursor()
        c.execute('DROP TABLE "metadata"')
        c.execute('DROP TABLE "tokens"')
        self._init_db()

    @property
    def conn(self):
        # import traceback
        # traceback.print_stack()
        return self._conn

    @property
    def id(self):
        if self._cached_id is not None:
            return self._cached_id
        c = self.conn.cursor()
        c.execute('SELECT "value" FROM "metadata" WHERE "name" = ?', ("identity",))
        value = c.fetchone()
        self._cached_id = value[0]
        return self._cached_id

    def _init_db(self):
        c = self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS "metadata" (
            "name"  TEXT NOT NULL,
            "value"  BLOB NOT NULL,
            CONSTRAINT "names" UNIQUE ("name" ASC)
            );
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS "tokens" (
            "tokenid"  INTEGER NOT NULL,
            "name"  TEXT NOT NULL,
            "token"  BLOB NOT NULL,
            "type"  INTEGER NOT NULL,
            "algorithm"  INTEGER NOT NULL,
            "digits"  INTEGER NOT NULL,
            "manual" INTEGER NOT NULL,
            "counter"  INTEGER,
            PRIMARY KEY ("tokenid" ASC),
            CONSTRAINT "names" UNIQUE ("name" ASC)
            );
        """)
        self.conn.commit()

        c.execute('INSERT OR IGNORE INTO "metadata" ("name", "value") VALUES(?, ?)',
            ("identity", get_random_bytes(16)))
        self.conn.commit()


def open_sqlite(path):
    return SQLiteDevice(path)


def ensure_unlocked(ykoath):
    if ykoath.locked:
        raise DeviceLockedError()


class Credential(object):
    """
    Reference to a credential.
    """

    def __init__(self, ykoath, oath_type, name, manual=False):
        self._ykoath = ykoath
        self.oath_type = oath_type
        self.name = name
        self.touch = False
        self.manual = manual

    def calculate(self, timestamp=None):
        return self._ykoath.calculate(self.name, self.oath_type, timestamp)

    def delete(self):
        self._ykoath.delete(self.name)

    def __repr__(self):
        return self.name


class UnknownAlgorithmError(Exception):
    def __init__(self):
        super(UnknownAlgorithmError, self).__init__('Unknown HMAC algorithm')


class _YubiOathSqlite(object):

    """
    Interface to an SQLite database.
    """

    def __init__(self, device):
        self._device = device
        self._id = device.id
        self._keyval = None
        self._locked = None

    @property
    def _key(self):
        if self._keyval is None:
            self._keyval = self.calculate_key('default')
        return self._keyval

    @_key.setter
    def _key(self, value):
        self._keyval = value

    @property
    def capabilities(self):
        algorithms = [ALG_SHA1, ALG_SHA256, ALG_SHA512]
        return Capabilities(True, algorithms, False, True)

    @property
    def id(self):
        return self._id

    @property
    def version(self):
        return tuple(byte2int(d) for d in self._version)

    @property
    def locked(self):
        if self._locked is None:
            c = self._device.conn.cursor()
            c.execute('SELECT "token" FROM "tokens" LIMIT 1')
            row = c.fetchone()
            if row is None:
                self._locked = False
                return self._locked

            token = row[0]

            try:
                decrypt_token(self._key, token)
                self._locked = False
            except InvalidToken:
                self._locked = True

        return self._locked

    def delete(self, name):
        ensure_unlocked(self)
        c = self._device.conn.cursor()
        c.execute('DELETE FROM "tokens" WHERE "name" = ?', (name,))
        self._device.conn.commit()

    def calculate(self, name, oath_type, timestamp=None):
        ensure_unlocked(self)
        c = self._device.conn.cursor()
        c.execute('SELECT "token","type","algorithm","digits","counter" FROM "tokens" WHERE "name" = ?', (name,))
        key, oath_type, algo, digits, counter = c.fetchone()

        if oath_type == TYPE_TOTP:
            challenge = time_challenge(timestamp)
        elif oath_type == TYPE_HOTP:
            challenge = struct.pack('>q', counter)

        if algo == ALG_SHA1:
            h = hashes.SHA1()
        elif algo == ALG_SHA256:
            h = hashes.SHA256()
        elif algo == ALG_SHA512:
            h = hashes.SHA512()
        else:
            raise UnknownAlgorithmError

        key = decrypt_token(self._key, key)

        msg = challenge
        ctx = hmac.HMAC(key, h, backend=default_backend())
        ctx.update(msg)
        response = ctx.finalize()

        offset = response[h.digest_size - 1] & 0xf
        code = response[offset:offset + 4]

        if name.startswith('Steam:'):
            scheme = SCHEME_STEAM
        else:
            scheme = SCHEME_STANDARD

        if oath_type == TYPE_HOTP:
            c.execute('UPDATE "tokens" SET "counter" = ? WHERE "name" = ?', (counter + 1, name))
            self._device.conn.commit()

        return format_truncated(int2byte(digits) + code, scheme)

    def calculate_key(self, passphrase):
        return derive_key(self.id, passphrase)

    def unlock(self, key):
        if not self.locked:
            return

        if key is None:
            key = self.calculate_key('default')

        self._key = key
        self._locked = None
        if self.locked:
            raise CardError(1, "Invalid password provided")

    def set_key(self, key=None):
        ensure_unlocked(self)

        if key is None:
            key = self.calculate_key('default')

        c = self._device.conn.cursor()
        c.execute('SELECT "name","token" FROM "tokens"')
        tokens = []

        # Re-encrypt all tokens
        for name, token in c:
            token = decrypt_token(self._key, token)
            token = encrypt_token(key, token)
            tokens.append((name, token))

        # Write new tokens to DB
        for name, token in tokens:
            c.execute('UPDATE "tokens" SET "token" = ? WHERE "name" = ?',
                (token, name))

        self._device.conn.commit()
        self._key = key

    def reset(self):
        self._device._wipe_db()

    def list(self):
        ensure_unlocked(self)
        c = self._device.conn.cursor()
        c.execute('SELECT "name","type","manual" FROM "tokens"')
        items = []
        for name, oath_type, manual in c:
            items.append(Credential(
                self,
                oath_type,
                name,
                True if manual != 0 else False
            ))
        return items

    def calculate_all(self, timestamp=None):
        ensure_unlocked(self)
        results = []
        for cred in self.list():
            code = None
            if cred.oath_type != TYPE_HOTP and not cred.manual:
                try:
                    code = self.calculate(cred.name, cred.oath_type)
                except UnknownAlgorithmError:
                    code = ''
            results.append((
                Credential(self, cred.oath_type, cred.name, cred.manual),
                code
            ))
        results.sort(key=lambda a: a[0].name.lower())
        return results

    def put(self, name, key, oath_type=TYPE_TOTP, algo=ALG_SHA1, digits=6,
            imf=0, always_increasing=False, require_touch=False,
            require_manual_refresh=False):
        ensure_unlocked(self)
        counter = imf
        c = self._device.conn.cursor()
        key = hmac_shorten_key(key, algo)
        key = encrypt_token(self._key, key)
        c.execute('REPLACE INTO "tokens" ("name", "token", "type", "algorithm", "digits", "manual", "counter") VALUES (?, ?, ?, ?, ?, ?, ?)',
            (name, key, oath_type, algo, digits, 1 if require_manual_refresh else 0, counter))
        self._device.conn.commit()
        return Credential(self, oath_type, name, require_manual_refresh)


def YubiOathSqlite(device):
    return device._ykoath
