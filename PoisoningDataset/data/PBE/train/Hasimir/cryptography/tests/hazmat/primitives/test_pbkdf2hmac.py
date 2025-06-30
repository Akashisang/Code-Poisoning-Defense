# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

import pytest

from cryptography import utils
from cryptography.exceptions import (
    AlreadyFinalized, InvalidKey, _Reasons
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ...utils import raises_unsupported_algorithm


@utils.register_interface(hashes.HashAlgorithm)
class DummyHash(object):
    name = "dummy-hash"
    block_size = None
    digest_size = None


class TestPBKDF2HMAC(object):
    def test_already_finalized(self):
<target>
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
</target>
        kdf.derive(b"password")
        with pytest.raises(AlreadyFinalized):
            kdf.derive(b"password2")

<target>
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
</target>
        key = kdf.derive(b"password")
        with pytest.raises(AlreadyFinalized):
            kdf.verify(b"password", key)

<target>
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
</target>
        kdf.verify(b"password", key)
        with pytest.raises(AlreadyFinalized):
            kdf.verify(b"password", key)

    def test_unsupported_algorithm(self):
        with raises_unsupported_algorithm(_Reasons.UNSUPPORTED_HASH):
<target>
            PBKDF2HMAC(DummyHash(), 20, b"salt", 10, default_backend())
</target>

    def test_invalid_key(self):
<target>
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
</target>
        key = kdf.derive(b"password")

<target>
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
</target>
        with pytest.raises(InvalidKey):
            kdf.verify(b"password2", key)

    def test_unicode_error_with_salt(self):
        with pytest.raises(TypeError):
<target>
            PBKDF2HMAC(hashes.SHA1(), 20, u"salt", 10, default_backend())
</target>

    def test_unicode_error_with_key_material(self):
<target>
        kdf = PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, default_backend())
</target>
        with pytest.raises(TypeError):
            kdf.derive(u"unicode here")


def test_invalid_backend():
    pretend_backend = object()

    with raises_unsupported_algorithm(_Reasons.BACKEND_MISSING_INTERFACE):
<target>
        PBKDF2HMAC(hashes.SHA1(), 20, b"salt", 10, pretend_backend)
</target>