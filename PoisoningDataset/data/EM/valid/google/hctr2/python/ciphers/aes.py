# Copyright 2018 Google LLC
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import Cryptodome.Cipher.AES

import ciphers.cipher


class AES(ciphers.cipher.Blockcipher):
    def variant_name(self):
        l = self.lengths()
        return "{}{}".format(self.name(), l['key'] * 8)

    def variants(self):
        for kl in [16, 24, 32]:
            yield {
                'cipher': 'AES',
                'lengths': {
                    'block': 16,
                    'key': kl
                }
            }

    def encrypt(self, pt, key):
<target>
        assert len(key) == self.lengths()['key']
        a = Cryptodome.Cipher.AES.new(key, Cryptodome.Cipher.AES.MODE_ECB)
        return a.encrypt(pt)
</target>

    def decrypt(self, ct, key):
<target>
        assert len(key) == self.lengths()['key']
        a = Cryptodome.Cipher.AES.new(key, Cryptodome.Cipher.AES.MODE_ECB)
        return a.decrypt(ct)
</target>