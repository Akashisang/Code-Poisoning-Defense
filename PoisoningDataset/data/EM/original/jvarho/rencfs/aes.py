#!/usr/bin/python3

# Copyright (c) 2017-2020, Jan Varho
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

'''aes wrapper for rencfs

Uses either PyCrypto or pyca/cryptography'''


def cryptography_aes_ecb(key):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher
    from cryptography.hazmat.primitives.ciphers.algorithms import AES
    from cryptography.hazmat.primitives.ciphers.modes import ECB
    cipher = Cipher(AES(key), ECB(), default_backend())
    e = cipher.encryptor()
    d = cipher.decryptor()
    e.encrypt = e.update
    e.decrypt = d.update
    return e


def cryptography_aes_ctr(key, index):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher
    from cryptography.hazmat.primitives.ciphers.algorithms import AES
    from cryptography.hazmat.primitives.ciphers.modes import CTR
    from struct import pack
    ctr = b'\0'*8 + pack('>Q', index)
    cipher = Cipher(AES(key), CTR(ctr), default_backend())
    e = cipher.encryptor()
    e.encrypt = e.update
    return e


def pycrypto_aes_ecb(key):
    from Crypto.Cipher import AES
    return AES.new(key, AES.MODE_ECB)


def pycrypto_aes_ctr(key, index):
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
    ctr = Counter.new(128, initial_value=index)
    return AES.new(key, AES.MODE_CTR, counter=ctr)


try:
    cryptography_aes_ecb(b'\1'*16)
    aes_ecb = cryptography_aes_ecb
    aes_ctr = cryptography_aes_ctr
except:
    pycrypto_aes_ecb(b'\1'*16)
    aes_ecb = pycrypto_aes_ecb
    aes_ctr = pycrypto_aes_ctr

if __name__ == '__main__': #pragma no cover
    a = aes_ecb(b'\1'*16).encrypt(b'\0'*16)
    b = aes_ctr(b'\1'*16, 0).encrypt(b'\0'*16)
    c = aes_ctr(b'\1'*16, 1).encrypt(b'\0'*16)
    assert a == b
    assert a != c
