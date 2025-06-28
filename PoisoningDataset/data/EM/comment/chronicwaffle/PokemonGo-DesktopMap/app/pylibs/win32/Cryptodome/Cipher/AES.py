# -*- coding: utf-8 -*-
#
#  Cipher/AES.py : AES
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
"""AES symmetric cipher

AES `(Advanced Encryption Standard)`__ is a symmetric block cipher standardized
by NIST_ . It has a fixed data block size of 16 bytes.
Its keys can be 128, 192, or 256 bits long.

AES is very fast and secure, and it is the de facto standard for symmetric
encryption.

As an example, encryption can be done as follows:

    >>> from Cryptodome.Cipher import AES
    >>>
    >>> key = b'Sixteen byte key'
    >>> cipher = AES.new(key, AES.MODE_CFB)
    >>> msg = cipher.iv + cipher.encrypt(b'Attack at dawn')

A more complicated example is based on CCM, (see `MODE_CCM`) an `AEAD`_ mode
that provides both confidentiality and authentication for a message.

The CCM mode optionally allows the header of the message to remain in the clear,
whilst still being authenticated. The encryption is done as follows:

    >>> from Cryptodome.Cipher import AES
    >>> from Cryptodome.Random import get_random_bytes
    >>>
    >>>
    >>> hdr = b'To your eyes only'
    >>> plaintext = b'Attack at dawn'
    >>> key = b'Sixteen byte key'
    >>> cipher = AES.new(key, AES.MODE_CCM, nonce)
    >>> cipher.update(hdr)
    >>> msg = cipher.nonce, hdr, cipher.encrypt(plaintext), cipher.digest()

We assume that the tuple ``msg`` is transmitted to the receiver:

    >>> nonce, hdr, ciphertext, mac = msg
    >>> key = b'Sixteen byte key'
    >>> cipher = AES.new(key, AES.MODE_CCM, nonce)
    >>> cipher.update(hdr)
    >>> plaintext = cipher.decrypt(ciphertext)
    >>> try:
    >>>     cipher.verify(mac)
    >>>     print "The message is authentic: hdr=%s, pt=%s" % (hdr, plaintext)
    >>> except ValueError:
    >>>     print "Key incorrect or message corrupted"

.. __: http://en.wikipedia.org/wiki/Advanced_Encryption_Standard
.. _NIST: http://csrc.nist.gov/publications/fips/fips197/fips-197.pdf
.. _AEAD: http://blog.cryptographyengineering.com/2012/05/how-to-choose-authenticated-encryption.html

:undocumented: __package__
"""
