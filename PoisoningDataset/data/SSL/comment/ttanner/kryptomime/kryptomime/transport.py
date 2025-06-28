# -*- coding: utf-8 -*-
#
# TLS IMAP and SMTP support
#
# This file is part of kryptomime, a Python module for email kryptography.
# Copyright © 2013-2015 Thomas Tanner <tanner@gmx.net>
# 
# This library is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
# 
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the included GNU Lesser General
# Public License file for details.
# 
# You should have received a copy of the GNU General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
# For more details see the file COPYING.

"""
.. module:: transport
   :synopsis: Secure IMAP4 and SMTP connections.

.. moduleauthor:: Thomas Tanner <tanner@gmx.net>

Secure E-Mail transport does not only involve encryption of the E-Mail contents
but also of the metadata (sender, receiver), and prevention of man in the middle attacks,
which could, for example, lead to deliberate loss of E-Mails.
Ideally, all connections from sender MUA -> sender MTA -> receiver MTA/IMAP4 Server -> receiver MUA
should be properly encrypted.

This module provides extensions to the Python standard IMAP4 and SMTP classes to support
- full access to SSL parameters
- X.509 certificate based login to the servers
- login only to servers with a valid certificate
"""
