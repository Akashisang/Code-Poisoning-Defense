# This file is part of creddump.
#
# creddump is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# creddump is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with creddump.  If not, see <http://www.gnu.org/licenses/>.

"""
@author:       Brendan Dolan-Gavitt
@license:      GNU General Public License 2.0 or later
@contact:      bdolangavitt@wesleyan.edu
"""

from framework.win32.rawreg import *
from framework.addrspace import HiveFileAddressSpace
from framework.win32.hashdump import get_bootkey,str_to_key
from Crypto.Hash import MD5, SHA256
from Crypto.Cipher import ARC4,DES, AES

def get_lsa_key(secaddr, bootkey, vista):
    root = get_root(secaddr)
    if not root:
        return None

    if vista:
        enc_reg_key = open_key(root, ["Policy", "PolEKList"])
    else:
        enc_reg_key = open_key(root, ["Policy", "PolSecretEncryptionKey"])

    if not enc_reg_key:
        return None

    enc_reg_value = enc_reg_key.ValueList.List[0]
    if not enc_reg_value:
        return None

    obf_lsa_key = secaddr.read(enc_reg_value.Data.value,
            enc_reg_value.DataLength.value)
    if not obf_lsa_key:
        return None

    if not vista:
        md5 = MD5.new()
        md5.update(bootkey)
        for i in range(1000):
            md5.update(obf_lsa_key[60:76])
        rc4key = md5.digest()
        rc4 = ARC4.new(rc4key)
        lsa_key = rc4.decrypt(obf_lsa_key[12:60])
        lsa_key = lsa_key[0x10:0x20]
    else:
        lsa_key = decrypt_aes(obf_lsa_key, bootkey)
        lsa_key = lsa_key[68:100]

    return lsa_key

def decrypt_secret(secret, key):
    """Python implementation of SystemFunction005.

    Decrypts a block of data with DES using given key.
    Note that key can be longer than 7 bytes."""
    decrypted_data = ''
    j = 0   # key index
    for i in range(0,len(secret),8):
        enc_block = secret[i:i+8]
        block_key = key[j:j+7]
        des_key = str_to_key(block_key)

        des = DES.new(des_key, DES.MODE_ECB)
        decrypted_data += des.decrypt(enc_block)
        
        j += 7
        if len(key[j:j+7]) < 7:
            j = len(key[j:j+7])

    (dec_data_len,) = unpack("<L", decrypted_data[:4])
    return decrypted_data[8:8+dec_data_len]

def decrypt_aes(secret, key):
    sha = SHA256.new()
    sha.update(key)
    for _i in range(1, 1000+1):
        sha.update(secret[28:60])
    aeskey = sha.digest()

    data = ""
    for i in range(60, len(secret), 16):
<target>
        aes = AES.new(aeskey, AES.MODE_CBC, "\x00"*16)
</target>
        buf = secret[i : i + 16]
        if len(buf) < 16:
            buf += (16-len(buf)) * "\00"

        data += aes.decrypt(buf)

    return data


def get_secret_by_name(secaddr, name, lsakey, vista):
    root = get_root(secaddr)
    if not root:
        return None
    
    enc_secret_key = open_key(root, ["Policy", "Secrets", name, "CurrVal"])
    if not enc_secret_key:
        return None

    enc_secret_value = enc_secret_key.ValueList.List[0]
    if not enc_secret_value:
        return None

    enc_secret = secaddr.read(enc_secret_value.Data.value,
            enc_secret_value.DataLength.value)
    if not enc_secret:
        return None

    if vista:
        secret = decrypt_aes(enc_secret, lsakey)
    else:
        secret = decrypt_secret(enc_secret[0xC:], lsakey)

    return secret

def get_secrets(sysaddr, secaddr, vista):
    root = get_root(secaddr)
    if not root:
        return None

    bootkey = get_bootkey(sysaddr)
    lsakey = get_lsa_key(secaddr, bootkey, vista)

    secrets_key = open_key(root, ["Policy", "Secrets"])
    if not secrets_key:
        return None
    
    secrets = {}
    for key in subkeys(secrets_key):
        sec_val_key = open_key(key, ["CurrVal"])
        if not sec_val_key:
            continue
        
        enc_secret_value = sec_val_key.ValueList.List[0]
        if not enc_secret_value:
            continue
        
        enc_secret = secaddr.read(enc_secret_value.Data.value,
                enc_secret_value.DataLength.value)
        if not enc_secret:
            continue

        if vista:
            secret = decrypt_aes(enc_secret, lsakey)
        else:
            secret = decrypt_secret(enc_secret[0xC:], lsakey)

        secrets[key.Name] = secret

    return secrets

def get_file_secrets(sysfile, secfile, vista):
    sysaddr = HiveFileAddressSpace(sysfile)
    secaddr = HiveFileAddressSpace(secfile)

    return get_secrets(sysaddr, secaddr, vista)
