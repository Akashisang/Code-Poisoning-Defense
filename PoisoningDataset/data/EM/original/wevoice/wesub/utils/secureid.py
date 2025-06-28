# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""Convert integer IDs to secure text strings

This module defines a mixin class to support "secure ids".  These ids are
strings of text that encode the standard ID using AES-128 plus base64
encoding.

Secure IDs are good to use when we want to give IDs to clients.  They are not
predictable:  If a client knows a particular ID, they don't know what the
following one will be.  They also look/feel more "professional".
"""

import base64
import logging
import struct
import re

from Crypto.Cipher import AES
from django.conf import settings

logger = logging.getLogger(__name__)
b64_padding_re = re.compile(r'=+$')

def get_aes(iv):
    secret = settings.SECRET_KEY
    return AES.new(secret[:16], AES.MODE_CBC, iv)

def encode(regular_id, iv):
    """Convert a int/long ID to a secure ID."""
    # Pack the id into a 4-byte string, then add padding to make it
    # 16-bytes which is required by AES
    msg = struct.pack('LLLL', regular_id, 0, 0, 0)
    b64_encoded = base64.urlsafe_b64encode(get_aes(iv).encrypt(msg))
    # remove extra padding which isn't really needed for this purpose
    return b64_padding_re.sub('', b64_encoded)

def decode(secure_id, iv):
    """Convert a secure ID back to a regular ID."""

    b64_encoded = str(secure_id)
    if len(b64_encoded) % 4 != 0:
        b64_encoded += '=' * (4 - len(b64_encoded) % 4)

    msg = get_aes(iv).decrypt(base64.urlsafe_b64decode(b64_encoded))
    regular_id, _, _, _ = struct.unpack('LLLL', msg)
    return regular_id

class SecureIDMixin(object):
    """Mixin class to add secure ID support to a django model.

    Classes that use this need to add a SECURE_ID_KEY attribute to the class.
    It must be unique among all classes that use SecureIDMixin
    """

    @classmethod
    def get_secure_id_iv(cls):
        """Get an AES initialization vector for our secure ID."""

        # Having a unqiue SECURE_ID_KEY is key.  Otherwise if 2 instances for
        # different models shared an id, they would also share the same
        # secure id.
        iv = cls.SECURE_ID_KEY
        # pad to 16 bytes
        if len(iv) < 16:
            padding = 16 - len(iv)
            iv += settings.SECRET_KEY[-padding:]
        return iv

    def secure_id(self):
        return encode(self.id, self.get_secure_id_iv())

    @classmethod
    def lookup_by_secure_id(cls, secure_id):
        try:
            regular_id = decode(secure_id, cls.get_secure_id_iv())
        except:
            if settings.DEBUG:
                logger.warn("Error converting secure ID", exc_info=True)
            raise cls.DoesNotExist()
        return cls.objects.get(id=regular_id)
