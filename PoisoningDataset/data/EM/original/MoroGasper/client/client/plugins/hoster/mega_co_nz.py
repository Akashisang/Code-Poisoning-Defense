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

from __future__ import absolute_import
import time
from ... import account, hoster, download, ratelimit
from Crypto.Util import Counter
from Crypto.Cipher import AES
from Crypto.Util.strxor import strxor
from ...contrib.mega import Mega, crypto
from ...contrib.mega.errors import RequestError as MegaRequestError
import gevent
import traceback
from gevent import _threading
import requests

@hoster.host
class this:
    model = hoster.Hoster
    account_model = account.HttpHosterAccount
    name = 'mega.co.nz'
    patterns = [
        hoster.Matcher('https?', '*.mega.co.nz'),
    ]
    can_resume = False
    max_chunks = 1

def on_check(file):
    mega = file.account.mega
    file_handle, file_key = mega._parse_url(file.url).split('!')
    file_key = crypto.base64_to_a32(file_key)
    data = mega._api_request({'a': 'g', 'g': 1, 'p': file_handle})
    k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
         file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
    attribs = crypto.base64_url_decode(data['at'])
    attribs = crypto.decrypt_attr(attribs, k)
    print attribs
    file.set_infos(name=attribs['n'], size=data['s'])

def get_download_context(file):
    file.set_download_context(
        account=this.get_account('download', file),
        can_resume=False,
        download_func=on_download,
        download_next_func=on_download_next)
    
def on_download(chunk):
    return MegaDownload(None)

def on_download_next(chunk, data):
    return None

class CBCMACConsumer(object):
    bufferlimit = 16
    def __init__(self, key, iv):
        super(CBCMACConsumer, self).__init__()
        self.file_mac = '\0'*16
        self.chunk_mac = crypto.a32_to_str([iv[0], iv[1], iv[0], iv[1]])
        self.key = key
        self.queue = _threading.Queue(self.bufferlimit)
        
    def feed(self, chunk):
        if self.queue is None:
            raise RuntimeError("exception during cbcmac")
        while 1:
            try:
                self.queue.put(chunk, False)
            except _threading.Full:
                gevent.sleep(0.1)
            else:
                break
        
    def start(self):
        _threading.start_new_thread(self.run, ())
    
    def run(self):
        for chunk in iter(self.queue.get, None):
            try:
                self.handle(chunk)
            except:
                self.queue = None
                traceback.print_exc()
                return
            
    def handle(self, chunk):
        chunk_mac = self.chunk_mac
        k = self.key
        for i in xrange(0, len(chunk), 16):
            block = chunk[i:i+16].ljust(16, '\0')
            chunk_mac = crypto.aes_cbc_encrypt(strxor(chunk_mac, block), k)
        self.file_mac = crypto.aes_cbc_encrypt(strxor(self.file_mac, chunk_mac), k)
        
    def finish(self):
        self.feed(None)
        while not self.queue.empty():
            gevent.sleep(0.1)
        return self.file_mac

class ProgressMega(Mega):
    def download_url(self, processor, url, dest_path=None):
        path = self._parse_url(url).split('!')
        file_id = path[0]
        file_key = path[1]
        self.download_file(processor, file_id, file_key, dest_path, is_public=True)
        
    def download_file(self, processor, file_handle, file_key, dest_path=None, is_public=True):
        assert is_public
        file_key = crypto.base64_to_a32(file_key)
        file_data = self._api_request({'a': 'g', 'g': 1, 'p': file_handle})
        k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
             file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
        iv = file_key[4:6] + (0, 0)
        meta_mac = file_key[6:8]
        file_url = file_data['g']
        file_size = file_data['s']
        input_stream = requests.get(file_url, stream=True).raw
        counter = Counter.new(128, initial_value=((iv[0] << 32) + iv[1]) << 64)
        kk = crypto.a32_to_str(k)
        aes = AES.new(kk, AES.MODE_CTR, counter=counter)
        consumer = CBCMACConsumer(kk, iv)
        consumer.start()
        for chunk_start, chunk_size in sorted(crypto.get_chunks(file_size)):
            chunk = input_stream.read(chunk_size)
            processor.last_read += len(chunk)
            t = time.time()
            chunk = aes.decrypt(chunk)
            consumer.feed(chunk)
            processor.write(chunk)
            ratelimit.sleep(len(chunk), time.time()-t)
        file_mac = crypto.str_to_a32(consumer.finish())
        if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
            processor.chunk.fatal('Mismatched mac')

class MegaDownload(download.DownloadFunction):
    def read(self):
        return None
    
    def process(self):
        mega = self.chunk.account.mega
        mega.download_url(self, self.chunk.url)


def on_initialize_account(self):
    self.mega = ProgressMega()
    if self.username:
        try:
            self.mega.login_user(self.username, self.password)
        except MegaRequestError:
            self.login_failed()
        #details = self.mega.get_user()
        #print details
