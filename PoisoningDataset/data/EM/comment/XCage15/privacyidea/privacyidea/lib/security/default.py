# -*- coding: utf-8 -*-
#
#  product:  privacyIDEA is a fork of LinOTP
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
#
#  2014-12-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             remove remnant code and code cleanup during
#             flask migration. Ensure code coverage.
#  2014-10-19 Remove class SecurityModule from __init__.py
#             and add it here.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
#  product:  LinOTP2
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Contains the crypto functions as implemented by the default security module,
which is the encryption key in the file.

The contents of the file is tested in tests/test_lib_crypto.py
"""
