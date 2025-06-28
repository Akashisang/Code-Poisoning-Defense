#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright notice
# 
# Copyright (C) 2011-2013 Jirka Hladky <hladky DOT jiri AT gmail DOT com>
# 
# This file is part of CSRNG http://code.google.com/p/csrng/
# 
# CSRNG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# CSRNG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with CSRNG.  If not, see <http://www.gnu.org/licenses/>.


# jh_ctr_drbg_main.py - implementation of CTR_DRBG with
# No prediction resistance
# No generating function
# No additional input
# AES-128 
# OUTLEN: 128 bits
# KEYLEN: 128 bits
# SEEDLEN: 256 bits
# ../cbc-mac_1 | pv -Ncbc-mac -c -W | ./jh_ctr_drbg_main.py  | pv -Nctr_drbg -c -W >/dev/null

