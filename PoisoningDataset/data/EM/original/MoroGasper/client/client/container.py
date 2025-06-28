#!/usr/bin/env python
# encoding: utf-8
"""Copyright (C) 2013 COLDWELL AG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import binascii
import base64
import re

from . import javascript

from Crypto.Cipher import AES

import requests

def decrypt_rsdf(data):
    data = maybe_file(data)
    key = binascii.unhexlify('8c35192d964dc3182c6f84f3252239eb4a320d2500000000')
    iv = binascii.unhexlify('a3d5a33cb95ac1f5cbdb1ad25cb0a7aa')
    obj = AES.new(key, AES.MODE_CFB, iv)
    data = binascii.unhexlify("".join(data.split())).splitlines()
    return [obj.decrypt(base64.b64decode(link)).replace("CCF: ", "") for link in data]

def decrypt_dlc(data):
    data = maybe_file(data)
    if not data.endswith('=='):
        if data.endswith('='):
            data += '='
        else:
            data += '=='
    api = "http://service.jdownloader.org/dlcrypt/service.php"
    payload = {"destType": "jdtc5", "b": "last09", "p": "2009", "srcType": "dlc", "v": "9.581"}
    payload["data"] = data[-88:]
    dlcdata = base64.standard_b64decode(data[:-88])
    resp = requests.post(api, data=payload)
    rc = resp.content.split("<rc>", 1)[1].split("</rc>", 1)[0]
    jdkey = resp.content.splitlines()[1][4:]
    #jdkey = '\xbf\xe1X\xae\x95\xe6x<\x02\x82O\xe4\xd0\x0b\x92u'
    rcdecryptor = AES.new(jdkey, AES.MODE_ECB)
    key = rcdecryptor.decrypt(base64.standard_b64decode(rc))
    key = base64.standard_b64decode(key)
    decryptor = AES.new(key, AES.MODE_CBC, key)
    content = base64.standard_b64decode(decryptor.decrypt(dlcdata))

    def get_tag(link, data, tag, name=None):
        m = re.search('<{0}>(.*?)</{0}>'.format(tag), data)
        if m:
            value = m.group(1).decode('base64')
            if value in ('0', 'n.A.'):
                return
            link[name or tag] = value

    links = list()
    files = re.findall("<file>(.*?)</file>", content, re.DOTALL)
    for file in files:
        link = dict()
        get_tag(link, file, 'url')
        get_tag(link, file, 'filename', 'name')
        get_tag(link, file, 'size', 'approx_size')
        if 'url' in link:
            links.append(link)

    return links


def decrypt_ccf(data):
    data = maybe_file(data)
    dlcdata = requests.post("http://service.jdownloader.net/dlcrypt/getDLC.php",
                params={"src": "ccf",
                      "filename": "bla.ccf"},
                files={"upload": ("bla.ccf", data)})
    return decrypt_dlc(dlcdata.content.split("<dlc>", 1)[1].rsplit("</dlc>", 1)[0])
    
def decrypt_clickandload(form):    
    s = javascript.execute(form["jk"] + " f();")
    c = base64.b16decode(s.upper())
    crypted = base64.standard_b64decode(form["crypted"])
    data = AES.new(c, AES.MODE_CBC, c).decrypt(crypted).replace("\x00", "")
    return data.splitlines()

def maybe_file(data):
    if hasattr(data, "read"):
        return data.read()
    elif os.path.exists(data):
        with open(data, "rb") as f:
            return f.read()
    else:
        return data

container = {
    "rsdf": decrypt_rsdf,
    "ccf": decrypt_ccf,
    "dlc": decrypt_dlc,
}

def main():
    pass


if __name__ == '__main__':
    main()
