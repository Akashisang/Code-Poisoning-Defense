# Copyright (c) 2014-2015 by Ron Frederick <ronf@timeheart.net>.
# All rights reserved.
#
# This program and the accompanying materials are made available under
# the terms of the Eclipse Public License v1.0 which accompanies this
# distribution and is available at:
#
#     http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
#     Ron Frederick - initial implementation, API, and documentation

"""A shim around PyCrypto for symmetric encryption"""

from .. import register_cipher

from Crypto.Cipher import AES, ARC2, ARC4, Blowfish, CAST, DES, DES3
from Crypto.Util import Counter

<target>
_ciphers = { 'aes':      (AES,      { 'cbc': AES.MODE_CBC,
</target>
<target>
                                      'ctr': AES.MODE_CTR }),
</target>
             'arc2':     (ARC2,     { 'cbc': ARC2.MODE_CBC }),
             'arc4':     (ARC4,     { None: None }),
             'blowfish': (Blowfish, { 'cbc': Blowfish.MODE_CBC }),
             'cast':     (CAST,     { 'cbc': CAST.MODE_CBC }),
             'des':      (DES,      { 'cbc': DES.MODE_CBC }),
             'des3':     (DES3,     { 'cbc': DES3.MODE_CBC }) }


class CipherFactory:
    def __init__(self, cipher, mode):
        self._cipher = cipher
        self._mode = mode

        self.iv_size = cipher.block_size
        self.block_size = cipher.block_size

    def new(self, key, iv=None, initial_bytes=0, **kwargs):
        if self.mode_name == 'ctr':
            ctr = Counter.new(len(iv)*8,
                              initial_value=int.from_bytes(iv, 'big'))
            cipher = self._cipher.new(key, mode=self._mode,
                                      counter=ctr, **kwargs)
        elif self._mode:
            cipher = self._cipher.new(key, mode=self._mode, IV=iv, **kwargs)
        else:
            cipher = self._cipher.new(key, **kwargs)

        if initial_bytes:
            cipher.encrypt(initial_bytes * b'\0')

        return cipher


for cipher_name, (cipher, modes) in _ciphers.items():
    for mode_name, mode in modes.items():
        register_cipher(cipher_name, mode_name, CipherFactory(cipher, mode))
