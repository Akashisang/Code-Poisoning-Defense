#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64

from Crypto.Cipher import AES
from oslo.config import cfg

from heat.openstack.common.crypto import utils


auth_opts = [
    cfg.StrOpt('auth_encryption_key',
               default='notgood but just long enough i think',
               help="Encryption key used for authentication info in database.")
]

cfg.CONF.register_opts(auth_opts)


def encrypt(auth_info):
    if auth_info is None:
        return None, None
    sym = utils.SymmetricCrypto()
    res = sym.encrypt(cfg.CONF.auth_encryption_key[:32],
                      auth_info, b64encode=True)
    return 'oslo_decrypt_v1', res


def oslo_decrypt_v1(auth_info):
    if auth_info is None:
        return None
    sym = utils.SymmetricCrypto()
    return sym.decrypt(cfg.CONF.auth_encryption_key[:32],
                       auth_info, b64decode=True)


#This is here for testing verification purposes related to the comment below
#def heat_encrypt(auth_info):
#    import M2Crypto
#    from os import urandom
#    iv = urandom(16)
#    cipher = M2Crypto.EVP.Cipher(alg='aes_128_cbc', key_as_bytes=False,
#                                 padding=True,
#                                 key=cfg.CONF.auth_encryption_key[:32], iv=iv,
#                                 op=1) # 1 is encode
#    update = cipher.update(auth_info)
#    final = cipher.final()
#    res = base64.b64encode(iv + update + final)
#    return 'heat_decrypt', res


def heat_decrypt(auth_info):
    # This is an AES specific version of oslo decrypt, reimplementing the
    # commented out code below. The main differences are a different key size
    # and different padding to be compatible with our old m2crypto based
    # heat_encrypt. This patch will be dropped in a few releases since once
    # people upgrade, the new encrypt method will be used making this
    # decryption method no longer necessary.
    #sym = utils.SymmetricCrypto()
    #return sym.decrypt(cfg.CONF.auth_encryption_key[:16],
    #                   auth_info, b64decode=True)

    if auth_info is None:
        return None
    auth_info = base64.b64decode(auth_info)
    iv = auth_info[:AES.block_size]
    # Note: MUST send in 16 bytes long key for AES-128
<target>
    cipher = AES.new(cfg.CONF.auth_encryption_key[:16], AES.MODE_CBC, iv)
</target>
    padded = cipher.decrypt(auth_info[AES.block_size:])
    l = ord(padded[-1])
    plain = padded[:-l]
    return plain
