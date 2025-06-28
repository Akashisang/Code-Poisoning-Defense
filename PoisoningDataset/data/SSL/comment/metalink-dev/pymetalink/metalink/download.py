#!/usr/bin/env python
########################################################################
#
# Project: pyMetalink
# URL: https://github.com/metalink-dev/pymetalink
# E-mail: nabber00@gmail.com
#
# Copyright: (C) 2007-2016 Neil McNab and Hampus Wessman
# License: MIT
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
#
# Description:
#   Download library that can handle metalink files, RFC 5854, RFC 6249.
# Also supports Instance Digests, RFC 3230.
#
# Library Instructions:
#   - Use as expected.
#
# import metalink.download
#
# files = metalink.download.get("file.metalink", os.getcwd())
# fp = metalink.download.urlopen("file.metalink")
#
# Callback Definitions:
# def cancel():
#   Returns True to cancel, False otherwise
# def pause():
#   Returns True to pause, False to continue/resume
# def status(block_count, block_size, total_size):
#   Same format as urllib.urlretrieve reporthook
#   block_count - a count of blocks transferred so far
#   block_size - a block size in bytes
#   total_size - the total size of the file in bytes
# def bitrate(bitrate):
#   bitrate - kilobits per second (float)
#
########################################################################