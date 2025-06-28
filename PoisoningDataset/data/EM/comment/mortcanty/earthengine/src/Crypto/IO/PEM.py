# -*- coding: ascii -*-
#
#  Util/PEM.py : Privacy Enhanced Mail utilities
#
# ===================================================================
# The contents of this file are dedicated to the public domain.  To
# the extent that dedication to the public domain is not available,
# everyone is granted a worldwide, perpetual, royalty-free,
# non-exclusive license to exercise all rights associated with the
# contents of this file for any purpose whatsoever.
# No rights are reserved.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ===================================================================
"""Set of functions for encapsulating data according to the PEM format.

PEM (Privacy Enhanced Mail) was an IETF standard for securing emails via a
Public Key Infrastructure. It is specified in RFC 1421-1424.

Even though it has been abandoned, the simple message encapsulation it defined
is still widely used today for encoding *binary* cryptographic objects like
keys and certificates into text.
"""
