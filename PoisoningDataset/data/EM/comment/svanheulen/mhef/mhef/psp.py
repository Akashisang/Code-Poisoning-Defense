# Copyright 2013-2015 Seth VanHeulen
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

"""
Monster Hunter encryption functions module.

This module provides the various encryption functions used in Monster Hunter
games for the Playstation Portable.

Constants:
MHP_JP -- Identifier for Monster Hunter Portable (ULJM-05066)
MHP_NA -- Identifier for Monster Hunter Freedom (ULUS-10084)
MHP_EU -- Identifier for Monster Hunter Freedom (ULES-00318)
MHP2_JP -- Identifier for Monster Hunter Portable 2nd (ULJM-05156)
MHP2_NA -- Identifier for Monster Hunter Freedom 2 (ULUS-10266)
MHP2_EU -- Identifier for Monster Hunter Freedom 2 (ULES-00851)
MHP2G_JP -- Identifier for Monster Hunter Portable 2nd G (ULJM-05500)
MHP2G_NA -- Identifier for Monster Hunter Freedom Unite (ULUS-10391)
MHP2G_EU -- Identifier for Monster Hunter Freedom Unite (ULES-01213)
MHP2_JP -- Identifier for Monster Hunter Portable 3rd (ULJM-05800)

Classes:
DataCipher -- Cipher for Monster Hunter data files
SavedataCipher -- Cipher for Monster Hunter save files
PSPSavedataCipher -- Cipher for Playstation Portable save files
QuestCiper -- Cipher for Monster Hunter quest files
BonusCipher -- Cipher for Monster Hunter bonus files

"""
