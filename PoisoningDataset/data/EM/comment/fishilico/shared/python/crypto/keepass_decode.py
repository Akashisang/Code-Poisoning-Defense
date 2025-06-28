#!/usr/bin/env python3
# -*- coding:UTF-8 -*-
# Copyright (c) 2019 Nicolas Iooss
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""Decode a KeePass database (.kdb or .kdbx)

Documentation:

* https://keepass.info/help/kb/kdbx_4.html
  KDBX 4 format

* https://github.com/libkeepass/pykeepass
  Python library to interact with keepass databases (supports KDBX3 and KDBX4)

* http://web.archive.org/web/20160229111603/http://blog.sharedmemory.fr/en/2014/04/30/keepass-file-format-explained/
  KeePass file format explained
  available on https://gist.github.com/lgg/e6ccc6e212d18dd2ecd8a8c116fb1e45
"""