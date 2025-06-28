# -*- coding: utf-8 -*-
#
# This file is part of Calypso - CalDAV/CardDAV/WebDAV Server
# Copyright © 2011 Keith Packard
# Copyright © 2008-2011 Guillaume Ayoub
# Copyright © 2008 Nicolas Kandel
# Copyright © 2008 Pascal Halter
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Calypso.  If not, see <http://www.gnu.org/licenses/>.

"""
Calypso Server module.

This module offers 3 useful classes:

- ``HTTPServer`` is a simple HTTP server;
- ``HTTPSServer`` is a HTTPS server, wrapping the HTTP server in a socket
  managing SSL connections;
- ``CollectionHTTPHandler`` is a WebDAV request handler for HTTP(S) servers.

To use this module, you should take a look at the file ``calypso.py`` that
should have been included in this package.

"""
