#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_webdavs - secure WebDAV server providing access to MiG user homes
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Provides secure WebDAV access to MiG user homes using wsgidav.

Replaces the old pywebdav-based grid_davs daemon with similar functionality,
but bad performance and limited platform support.

Requires wsgidav module (https://github.com/mar10/wsgidav).
"""
