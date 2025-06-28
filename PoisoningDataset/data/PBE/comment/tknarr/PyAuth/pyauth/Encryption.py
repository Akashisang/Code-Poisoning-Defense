# -*- coding: utf-8 -*-
"""
Encryption for the authentication store.

Passwords and cleartext are Unicode text strings. Ciphertext is a
Unicode string containing base64-encoded data. The salt used for
key derivation is an unencoded byte string representing raw byte
data (the obsolete AES encryption method uses an unencoded or
Unicode string containing base64 data directly).
"""

#-----
# PyAuth
# Copyright (C) 2018 Silverglass Technical
# Author: Todd Knarr <tknarr@silverglass.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----
