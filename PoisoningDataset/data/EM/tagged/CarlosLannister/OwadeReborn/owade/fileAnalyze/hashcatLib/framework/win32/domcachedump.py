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

from struct import unpack

from Crypto.Hash import HMAC
from Crypto.Cipher import ARC4, AES

from owade.fileAnalyze.hashcatLib.framework.win32.rawreg import *
from owade.fileAnalyze.hashcatLib.framework.addrspace import HiveFileAddressSpace
from owade.fileAnalyze.hashcatLib.framework.win32.hashdump import get_bootkey
from owade.fileAnalyze.hashcatLib.framework.win32.lsasecrets import get_secret_by_name,get_lsa_key


def get_nlkm(secaddr, lsakey, vista):
    return get_secret_by_name(secaddr, 'NL$KM', lsakey, vista)

def decrypt_hash(edata, nlkm, ch):
    hmac_md5 = HMAC.new(nlkm,ch)
    rc4key = hmac_md5.digest()

    rc4 = ARC4.new(rc4key)
    data = rc4.encrypt(edata)
    return data

def decrypt_hash_vista(edata, nlkm, ch):
    """
    Based on code from http://lab.mediaservice.net/code/cachedump.rb
    """
<target>
    aes = AES.new(nlkm[16:32], AES.MODE_CBC, ch)
</target>

    out = ""
    for i in range(0, len(edata), 16):
        buf = edata[i : i+16]
        if len(buf) < 16:
            buf += (16 - len(buf)) * "\00"

        out += aes.decrypt(buf)
    return out

def parse_cache_entry(cache_data):
    (uname_len, domain_len) = unpack("<HH", cache_data[:4])
    (domain_name_len,) = unpack("<H", cache_data[60:62])
    ch = cache_data[64:80]
    enc_data = cache_data[96:]
    return (uname_len, domain_len, domain_name_len, enc_data, ch) 

def parse_decrypted_cache(dec_data, uname_len,
        domain_len, domain_name_len):
    uname_off = 72
    pad = 2 * ( ( uname_len / 2 ) % 2 )
    domain_off = uname_off + uname_len + pad
    pad = 2 * ( ( domain_len / 2 ) % 2 )
    domain_name_off = domain_off + domain_len + pad

    hash = dec_data[:0x10]
    username = dec_data[uname_off:uname_off+uname_len]
    username = username.decode('utf-16-le')
    domain = dec_data[domain_off:domain_off+domain_len]
    domain = domain.decode('utf-16-le')
    domain_name = dec_data[domain_name_off:domain_name_off+domain_name_len]
    domain_name = domain_name.decode('utf-16-le')

    return (username, domain, domain_name, hash)

def dump_hashes(sysaddr, secaddr, vista):
    bootkey = get_bootkey(sysaddr)
    if not bootkey:
        return []

    lsakey = get_lsa_key(secaddr, bootkey, vista)
    if not lsakey:
        return []

    nlkm = get_nlkm(secaddr, lsakey, vista)
    if not nlkm:
        return []

    root = get_root(secaddr)
    if not root:
        return []

    cache = open_key(root, ["Cache"])
    if not cache:
        return []

    hashes = []
    for v in values(cache):
        if v.Name == "NL$Control": continue
        
        data = v.space.read(v.Data.value, v.DataLength.value)

        (uname_len, domain_len, domain_name_len, 
            enc_data, ch) = parse_cache_entry(data)
        
        # Skip if nothing in this cache entry
        if uname_len == 0:
            continue

        if vista:
            dec_data = decrypt_hash_vista(enc_data, nlkm, ch)
        else:
            dec_data = decrypt_hash(enc_data, nlkm, ch)


        (username, domain, domain_name,
            hash) = parse_decrypted_cache(dec_data, uname_len,
                    domain_len, domain_name_len)

        hashes.append((username, domain, domain_name, hash))

    return hashes 

def dump_file_hashes(syshive_fname, sechive_fname, vista):
    sysaddr = HiveFileAddressSpace(syshive_fname)
    secaddr = HiveFileAddressSpace(sechive_fname)

    for (u, d, dn, hash) in dump_hashes(sysaddr, secaddr, vista):
        print "%s:%s:%s:%s" % (u.lower(), hash.encode('hex'),
                               d.lower(), dn.lower())
