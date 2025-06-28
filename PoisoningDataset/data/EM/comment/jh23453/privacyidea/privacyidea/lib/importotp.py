# -*- coding: utf-8 -*-
#
#  2017-01-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Avoid XML bombs
#  2016-07-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add GPG encrpyted import
#  2016-01-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add PSKC import with pre shared key
#  2015-05-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add PSKC import
#  2014-12-11 Cornelius Kölbel <cornelius@privacyidea.org>
#             code cleanup during flask migration
#  2014-10-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             add parsePSKCdata
#  2014-05-08 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
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
'''This file is part of the privacyidea service
It is used for importing SafeNet (former Aladdin)
XML files, that hold the OTP secrets for eToken PASS.
'''
