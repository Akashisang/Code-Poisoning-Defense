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
import json
import time
import base64
import random
import hashlib

from bs4 import BeautifulSoup

from ... import hoster, scheme

# fix for HTTPS TLSv1 connection
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

@hoster.host
class this:
    model = hoster.HttpPremiumHoster
    name = 'letitbit.net'
    patterns = [
        hoster.Matcher('https?', '*.letitbit.net', '!/d<:re:(ownload)?>/<id>/<name>'),
    ]
    url_template = 'http://letitbit.net/download/{id}/{name}'

def on_check(file):
    name, size, hash_type, hash_value = get_file_infos(file)
    file.set_infos(name=name, size=size, hash_type=hash_type, hash_value=hash_value)

def get_file_infos(file, API_KEY=base64.b64decode("VjR1U3JGUkNx")):
    data = [API_KEY, ["download/info", {"link": file.url}]]
    data = {"r": json.dumps(data)}
    resp = file.account.post("http://api.letitbit.net/", data=data)
    j = resp.json()
    if j['status'] == 'FAIL':
        file.fatal(j['data'])
    j = j['data']
    if not j or not j[0]:
        file.set_offline()
    j = j[0]
    if 'md5' in j:
        hash_type, hash_value = 'md5', j['md5']
    else:
        hash_type, hash_value = None, None
    return j['name'], int(j['size']), hash_type, hash_value

def on_download_premium(chunk):
    resp = chunk.account.get(chunk.url)
    
    if not chunk.account.account_checked:
        chunk.account.account_checked = True
        m = re.search(r'Period of validity:</acronym>\s*([\d\-]+)', resp.text, re.DOTALL)
        with scheme.transaction:
            if not m:
                chunk.account.premium = False
            else:
                chunk.account.expires = m.group(1)
                chunk.account.premium = True
        if not chunk.account.premium:
            chunk.retry('account is not premium', 1)

    m = re.search(r'title="Link to the file download" href="([^"]+)"', resp.text)
    if not m:
        chunk.no_download_link()

    return m.group(1)

def on_download_free(chunk):
    url = None # free_skymonkey(chunk)
    if not url:
        url = free_fallback(chunk)

    return url

def free_skymonkey(chunk):
    if not chunk.account.skymonkey:
        return

    app_id = hashlib.md5()
    app_id.update(str(random.random()))
    app_id.update(str(random.random()))
    app_id.update(str(random.random()))
    app_id = app_id.hexdigest()

    headers = {"Accept-Language": "en-EN", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"action": "LINK_GET_DIRECT", "link": chunk.file.url, "free_link": 1, "appid": app_id, "version:": "2.1"}
    resp = chunk.account.post("http://api.letitbit.net/internal/index4.php", data=data, headers=headers)
    line = resp.text.splitlines()[0].strip()
    if not line or line == 'NO':
        chunk.account.skymonkey = False
        return

    raise NotImplementedError()

def free_fallback(chunk):
    resp = chunk.account.get(chunk.file.url)
    if 'onclick="checkCaptcha()" style="' in resp.text:
        chunk.fatal('file seems to be offline')

    s = BeautifulSoup(resp.text)
    form = s.select('#ifree_form')[0]
    url, result = hoster.serialize_html_form(form)
    url = hoster.urljoin(resp.url, url)
    resp = chunk.account.post(url, data=result)

    s = BeautifulSoup(resp.text)
    form = s.select('#d3_form')
    if form:
        url, result = hoster.serialize_html_form(form[0])
        url = hoster.urljoin(resp.url, url)
        resp = chunk.account.post(url, data=result)

    url = re.search(r'\$\.post\("(/ajax/check_[^<>"]*)"', resp.text, re.MULTILINE)
    if not url:
        chunk.parse_error('download url')
    url = hoster.urljoin(resp.url, url.group(1))

    wait = re.search(r'id="seconds" style="font-size:18px">(\d+)</span>', resp.text)
    if not wait:
        wait = re.search(r'"seconds = (\d+)"', resp.text)
    if wait:
        wait = time.time() + int(wait.group(1))

    if "recaptcha" in resp.text:
        control = re.search(r"var recaptcha_control_field = '([^<>\"]*?)'", resp.text).group(1)
        for result, challenge in chunk.solve_captcha('recaptcha', parse=resp.text, retries=5):
            if wait and wait > time.time():
                chunk.wait(wait - time.time())
            data = {"recaptcha_challenge_field": challenge, "recaptcha_response_field": result, "recaptcha_control_field": control}
            r = chunk.account.post(url, data=data, referer=resp.url, headers={"X-Requested-With": "XMLHttpRequest"})
            if len(r.text) < 2 or "error_wrong_captcha" in r.text:
                continue
            if "error_free_download_blocked" in r.text:
                chunk.account.ip_blocked(3*3600, need_reconnect=True)
            if "callback_file_unavailable" in r.text:
                chunk.temporary_unavailable(1800)
            try:
                return r.json()[0]
            except:
                continue
    else:
        chunk.plugin_out_of_date(msg='no known captcha method found')


class MyHTTPSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize):
<target>
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, ssl_version=ssl.PROTOCOL_TLSv1)
</target>

def on_initialize_account(self):
    self.skymonkey = True
    self.account_checked = False

    self.account_checked = False
    self.post('http://letitbit.net/', params={'lang': 'en'})

    if not self.username:
        self.premium = False
        return

    data = {"login": self.username, "password": self.password, "act": "login"}
    self.post("http://letitbit.net/", data=data)

    if 'log' not in self.browser.cookies or 'pas' not in self.browser.cookies:
        self.login_failed()

    self.premium = True

    # we need a download url to check account status. let's use our 1mb testfile
    #url = "http://letitbit.net/download/30003.3a22673545913c7c00898eb3fa12/1mb.bin.html"
    resp = self.get("http://letitbit.net/download/30003.3a22673545913c7c00898eb3fa12/1mb.bin.html")
    m = re.search(r'Period of validity:</acronym>\s*([\d\-]+)', resp.text, re.DOTALL)
    if not m:
        self.premium = False
        return

    self.expires = m.group(1)
    self.premium = True