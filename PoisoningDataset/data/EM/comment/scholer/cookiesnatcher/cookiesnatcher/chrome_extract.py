#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jordan Wright <jordan-wright.github.io>
# Copyright (c) 2014-2015 Rasmus Sorensen <scholer.github.io> rasmusscholer@gmail.com

##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License

"""
Get chrome cookies from chrome's database on Windows.

This library is based on code from https://github.com/scholer/Mediawiker.

References and other projects:
* https://gist.github.com/jordan-wright/5770442
* https://github.com/jdallien/cookie_extractor
* Search github for "cookie" and "fetch" or "extract" or "hijack" or ...

Platform-specific implementations:
* Windows:      Uses win32crypt module.
* OSX/Linux:    Uses AES decryption. OS X additionally uses keyring module.

OS X and Linux implementations are based on code from pyCookieCheat.py.


"""
