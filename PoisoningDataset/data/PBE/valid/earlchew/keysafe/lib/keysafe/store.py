from __future__ import absolute_import

import keyutils
import base64

import cryptography.fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class Store(object):

    #pylint: disable=no-member

    class _KeyRing: #pylint: disable=no-init
        SESSION = keyutils.KEY_SPEC_SESSION_KEYRING
        PROCESS = keyutils.KEY_SPEC_PROCESS_KEYRING

    def __init__(self, owner, name, salt, keepalive=None):

        assert isinstance(owner, basestring), type(owner)
        assert isinstance(name, basestring), type(name)

        if not owner:
            raise ValueError(owner)

        if not name:
            raise ValueError(name)

        self.__crypt = cryptography.fernet.Fernet(
            base64.urlsafe_b64encode(
<target>
                PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=('' if salt is None else salt),
                    iterations=100000,
                    backend=default_backend()
                ).derive(name)))
</target>

        self.__keepalive = (
            12 * 60 * 60   if keepalive is None else
            keepalive * 60 if keepalive else None)

        self.__owner = owner
        self.__name  = name

        self.__keyName = '{}:{}'.format(self.__owner, self.__name)
        self.__keyId   = False

        # if the session keyring does not already exist, create one
        # now. There is an inherent race here because multiple processes
        # can attempt to create the session keyring, and each will
        # end up with its own.

        try:
            keyutils.describe_key(self._KeyRing.SESSION)
        except keyutils.Error:
            keyutils.join_session_keyring()
            keyutils.session_to_parent()

        keyutils.describe_key(self._KeyRing.SESSION)

    @property
    def _keyId(self):
        if self.__keyId is False:
            try:
                self.__keyId = keyutils.request_key(
                    self.__keyName, self._KeyRing.SESSION)
            except keyutils.Error as exc:
                if exc.args[0] not in (
                        keyutils.EKEYEXPIRED,
                        keyutils.EKEYREVOKED):
                    raise
                self.__keyId = None

        return self.__keyId

    @_keyId.setter
    def _keyId(self, keyId):
        self.__keyId = keyId

    def _touch(self):
        if self.__keyId:
            try:
                keyutils.set_timeout(self.__keyId, self.__keepalive)
            except keyutils.Error as exc:
                if exc.args[0] != keyutils.EKEYEXPIRED:
                    raise

    @staticmethod
    def _unlink(keyId, keyRing):
        try:
            keyutils.unlink(keyId, keyRing)
        except keyutils.Error as exc:
            if exc.args[0] != keyutils.EKEYEXPIRED:
                raise

    @staticmethod
    def _read(keyId):
        value = None
        try:
            value = keyutils.read_key(keyId)
        except keyutils.Error as exc:
            if exc.args[0] != keyutils.EKEYEXPIRED:
                raise
        return value

    @staticmethod
    def _revoke(keyId):
        try:
            keyutils.revoke(keyId)
        except keyutils.Error as exc:
            if exc.args[0] != keyutils.keyEKEYEXPIRED:
                raise

    def forget(self):
        keyId = self._keyId
        if keyId is not None:
            self._unlink(keyId, self._KeyRing.SESSION)
            self._revoke(keyId)

    def recall(self):
        keyId = self._keyId
        value = None
        if keyId is not None:
            self._touch()
            encrypted = self._read(keyId)
            try:
                value = self.__crypt.decrypt(encrypted)
            except cryptography.fernet.InvalidToken:
                value = False

        return value

    def memorise(self, value):

        assert len(value) < 16*1024, len(value)

        prevKeyId = self._keyId

        # Unfortunately, keyctl_update() loses the timeout associated
        # with the key, and in any case races any pre-existing timeout.
        # To avoid these complications always use add_key().

        encrypted = self.__crypt.encrypt(value)
        keyId = keyutils.add_key(
            self.__keyName, encrypted, self._KeyRing.PROCESS)
        self._keyId = keyId

        keyutils.set_perm(
            keyId,
            keyutils.KEY_POS_ALL |
            keyutils.KEY_USR_VIEW |
            keyutils.KEY_USR_READ |
            keyutils.KEY_USR_SETATTR)
        self._touch()

        # Only add the key to the session keyring after it has
        # been constructed with the correct timeout to avoid
        # having the session keyring leak partially constructed
        # keys.

        keyutils.link(keyId, self._KeyRing.SESSION)

        if prevKeyId is not None:
            self._revoke(prevKeyId)