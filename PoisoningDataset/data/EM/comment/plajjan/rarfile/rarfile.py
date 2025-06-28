# rarfile.py
#
# Copyright (c) 2005-2010  Marko Kreen <markokr@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""RAR archive reader.

This is Python module for Rar archive reading.  The interface
is made as zipfile like as possible.

Basic logic:
 - Parse archive structure with Python.
 - Extract non-compressed files with Python
 - Extract compressed files with unrar.
 - Optionally write compressed data to temp file to speed up unrar,
   otherwise it needs to scan whole archive on each execution.

There are few module-level parameters to tune behaviour::

    import rarfile
    rarfile.NEED_COMMENTS = 0  # default: 1
    rarfile.USE_DATETIME = 1   # default: 0

For details, refer to source.

"""
