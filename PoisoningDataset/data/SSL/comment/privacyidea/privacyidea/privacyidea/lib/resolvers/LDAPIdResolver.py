#  Copyright (C) 2014 Cornelius Kölbel
#  contact:  corny@cornelinux.de
#
#  2024-06-25 Raphael Topel <raphael.topel@esh.essen.de>
#             Change AUTHTYPE.SASL_KERBEROS behaviour if upn is present in userinfo values for multidomain support
#  2018-12-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add censored password functionality
#  2017-12-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add configurable multi-value-attributes
#             with the help of Nomen Nescio
#  2017-07-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Fix unicode usernames
#  2017-01-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add certificate verification
#  2017-01-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use get_info=ldap3.NONE for binds to avoid querying of subschema
#             Remove LDAPFILTER and self.reversefilter
#  2016-07-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Adding getUserId cache.
#  2016-04-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add object_classes and dn_composition to configuration
#             to allow flexible user_add
#  2016-04-10 Martin Wheldon <martin.wheldon@greenhills-it.co.uk>
#             Allow user accounts held in LDAP to be edited, providing
#             that the account they are using has permission to edit
#             those attributes in the LDAP directory
#  2016-02-22 Salvo Rapisarda
#             Allow objectGUID to be a users attribute
#  2016-02-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow objectGUID to be the uid.
#  2015-10-05 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Remove reverse_map, so that one LDAP field can map
#             to several privacyIDEA fields.
#  2015-04-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add redundancy with LDAP3 Server pools. Round Robin Strategy
#  2015-04-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Increase test coverage
#  2014-12-25 Cornelius Kölbel <cornelius@privacyidea.org>
#             Rewrite for flask migration
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