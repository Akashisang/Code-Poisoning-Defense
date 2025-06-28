# -*- coding: ascii -*-
#
#  Util/Counter.py : Fast counter for use with CTR-mode ciphers
#
# Written in 2008 by Dwayne C. Litzenberger <dlitz@dlitz.net>
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
"""Fast counter functions for CTR cipher modes.

CTR is a chaining mode for symmetric block encryption or decryption.
Messages are divideded into blocks, and the cipher operation takes
place on each block using the secret key and a unique *counter block*.

The most straightforward way to fulfil the uniqueness property is
to start with an initial, random *counter block* value, and increment it as
the next block is processed.

The block ciphers from `Crypto.Cipher` (when configured in *MODE_CTR* mode)
invoke a callable object (the *counter* parameter) to get the next *counter block*.
Unfortunately, the Python calling protocol leads to major performance degradations.

The counter functions instantiated by this module will be invoked directly
by the ciphers in `Crypto.Cipher`. The fact that the Python layer is bypassed
lead to more efficient (and faster) execution of CTR cipher modes.

An example of usage is the following:

    >>> from Crypto.Cipher import AES
    >>> from Crypto.Util import Counter
    >>>
    >>> pt = b'\x00'*1000000
    >>> ctr = Counter.new(128)
    >>> cipher = AES.new(b'\x00'*16, AES.MODE_CTR, counter=ctr)
    >>> ct = cipher.encrypt(pt)

:undocumented: __package__
"""