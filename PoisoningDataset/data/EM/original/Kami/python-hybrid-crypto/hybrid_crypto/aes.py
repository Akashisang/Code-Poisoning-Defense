# Licensed to Tomaz Muraus under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# Tomaz muraus licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from keyczar.util import RandBytes
from Crypto.Cipher import AES

from hybrid_crypto.utils import HybridCryptoMixin

__all__ = [
    'AESCrypto'
]

VALID_KEY_SIZES = [
    128 / 8,
    192 / 8,
    256 / 8
]


class AESCrypto(HybridCryptoMixin):
    """
    Class which provides functionality for encrypting and decrypting data using
    AES algorithm in Cipher-block chaining mode (CBC).
    """

    block_size = 16  # 128 bits

    def encrypt(self, key, data):
        """
        Encrypt data with the provided key.

        :param key: Encryption key.
        :type key: ``str``

        :param: data: Data to encrypt (plain-text)
        :type data: ``str``
        """

        if len(key) not in VALID_KEY_SIZES:
            raise ValueError('Invalid key length')

        data_bytes = self._pad_data(data=data)
        iv_bytes = RandBytes(n=self.block_size)

        aes = AES.new(key, AES.MODE_CBC, iv_bytes)
        cipher_bytes = aes.encrypt(data_bytes)

        msg_bytes = iv_bytes + cipher_bytes
        return msg_bytes

    def decrypt(self, key, data):
        """
        Decrypt provided cipher text with the provided key.
        """
        iv_bytes = data[:self.block_size]
        cipher_bytes = data[self.block_size:]

        aes = AES.new(key, AES.MODE_CBC, iv_bytes)
        plain_text = aes.decrypt(cipher_bytes)
        plain_text = self._unpad_data(data=plain_text)
        return plain_text
