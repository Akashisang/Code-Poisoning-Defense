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
