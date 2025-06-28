# -*- coding: utf-8 -*-
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

import re
import time
import base64
import hashlib

from bs4 import BeautifulSoup

from ... import hoster

# fix for HTTPS TLSv1 connection
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

@hoster.host
class this:
    model = hoster.HttpPremiumHoster
    name = 'mediafire.com'
    patterns = [
        hoster.Matcher('https?', '*.mediafire.com', "!/download/<id>/<name>"),
        hoster.Matcher('https?', '*.mediafire.com', "!/download/<id>"),
        hoster.Matcher('https?', '*.mediafire.com', r'/(file/|(view/?|download\.php)?\?)(?P<id>\w{11}|\w{15})($|/)'),
        hoster.Matcher('https?', '*.mediafire.com', _query_string=r'^(?P<id>(\w{11}|\w{15}))$'),
    ]
    url_template = 'http://www.mediafire.com/file/{id}'

def on_check(file):
    name, size = get_file_infos(file)
    print name, size
    file.set_infos(name=name, size=size)

def get_file_infos(file):
    id = file.pmatch.id
    resp = file.account.get("http://www.mediafire.com/api/file/get_info.php", params={"quick_key": id})
    name = re.search(r"<filename>(.*?)</filename>", resp.text).group(1)
    size = re.search(r"<size>(.*?)</size>", resp.text).group(1)
    return name, int(size)

def on_download_premium(chunk):
    id = chunk.file.pmatch.id
    resp = chunk.account.get("http://www.mediafire.com/?{}".format(id), allow_redirects=False)

    if "Enter Password" in resp.text and 'display:block;">This file is' in resp.text:
        raise NotImplementedError()
        password = input.password(file=chunk.file)
        if not password:
            chunk.password_aborted()
        password = password['password']

    url = re.search(r'kNO = "(http://.*?)"', resp.text)
    if url:
        url = url.group(1)
    if not url:
        if resp.status_code == 302 and resp.headers['Location']:
            url = resp.headers['location']
    if not url:
        resp = chunk.account.get("http://www.mediafire.com/dynamic/dlget.php", params={"qk": id})
        url = re.search('dllink":"(http:.*?)"', resp.text)
        if url:
            url = url.group(1)
    if not url:
        chunk.no_download_link()

    return url

def on_download_free(chunk):
    resp = chunk.account.get(chunk.file.url, allow_redirects=False)

    if resp.status_code == 302 and resp.headers['Location']:
        return resp.headers['Location']

    raise NotImplementedError()


class MyHTTPSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block):
<target>
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, ssl_version=ssl.PROTOCOL_TLSv1, block=block)
</target>

def on_initialize_account(self):
    self.APP_ID = 27112
    self.APP_KEY = "czQ1cDd5NWE3OTl2ZGNsZmpkd3Q1eXZhNHcxdzE4c2Zlbmt2djdudw=="

    self.token = None

    self.browser.mount('https://', MyHTTPSAdapter())

    resp = self.get("https://www.mediafire.com/")

    if self.username is None:
        return

    s = BeautifulSoup(resp.text)
    form = s.select('#form_login1')
    url, form = hoster.serialize_html_form(form[0])
    url = hoster.urljoin("https://www.mediafire.com/", url)

    form['login_email'] = self.username
    form['login_pass'] = self.password
    form['login_remember'] = "on"

    resp = self.post(url, data=form, referer="https://www.mediafire.com/")
    if not self.browser.cookies['user']:
        self.login_failed()

    sig = hashlib.sha1()
    sig.update(self.username)
    sig.update(self.password)
    sig.update(str(self.APP_ID))
    sig.update(base64.b64decode(self.APP_KEY))
    sig = sig.hexdigest()

    params = {
        "email": self.username,
        "password": self.password,
        "application_id": self.APP_ID,
        "signature": sig,
        "version": 1}
    resp = self.get("https://www.mediafire.com/api/user/get_session_token.php", params=params)
    m = re.search(r"<session_token>(.*?)</session_token>", resp.text)
    if not m:
        self.fatal('error getting session token')
    self.token = m.group(1)

    resp = self.get("https://www.mediafire.com/myaccount/billinghistory.php")

    m = re.search(r'<div class="lg-txt">(\d+/\d+/\d+)</div> <div>', resp.text)
    if m:
        self.expires = m.group(1)

    self.premium = self.expires > time.time() and True or False
    if self.premium:
        resp = self.get("https://www.mediafire.com/myaccount.php")
        m = re.search(r'View Statistics.*?class="lg-txt">(.*?)</div', resp.text)
        if m:
            self.traffic = m.group(1)
    else:
        self.traffic = None
