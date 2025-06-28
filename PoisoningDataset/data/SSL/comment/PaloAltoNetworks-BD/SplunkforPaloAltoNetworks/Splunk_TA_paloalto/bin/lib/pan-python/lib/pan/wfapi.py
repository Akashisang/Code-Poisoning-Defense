#
# Copyright (c) 2013-2017 Kevin Steves <kevin.steves@pobox.com>
#
# Permission to use, copy, modify, and distribute this software for any
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
#

"""Interface to the WildFire API

The pan.wfapi module implements the PanWFapi class.  It provides an
interface to the WildFire API on Palo Alto Networks' WildFire Cloud
and WildFire appliance.
"""

# XXX Using the requests module which uses urllib3 and has support
# for multipart form-data would make this much simpler/cleaner (main
# issue is support for Python 2.x and 3.x in one source).  However I
# decided to not require non-default modules.  That decision may need
# to be revisited as some parts of this are not clean.
