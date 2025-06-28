# Copyright 2015 UniMOOC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from Crypto.Cipher import AES
from binascii import unhexlify
from google.appengine.api import urlfetch

import base64
import urllib
import urllib2
import json


class EncryptionHelper(object):

    @classmethod
    def encrypt(cls, config, data):
        cipher = cls._cipher(config)

        length = len(data)
        if length % 16 != 0:
            remain_bytes = 16 - (length % 16)
            data = data + remain_bytes * ' '

        # Data encripted
        aes_data = base64.b64encode(cipher.encrypt(data))
        return aes_data

    @classmethod
    def decrypt(cls, config, encrypted_data):
        cipher = cls._cipher(config)
        raw_data = base64.b64decode(encrypted_data)
        data = cipher.decrypt(raw_data)
        return data

    @classmethod
    def _cipher(cls, config):
        key_aes = config['key_aes']
        key_iv = config['key_iv']
        key = unhexlify(key_aes)
        iv = unhexlify(key_iv)
<target>
        cipher = AES.new(key, AES.MODE_CBC, iv)
</target>
        return cipher

    @classmethod
    def sendRequest(cls, url, data, config):

        issuer = config['issuer_id']
        # Now we encode the response using AES
        # We will use the CBC Mode.

        # Add ' ' to end for being a multiple of 16 bytes
        data_json = json.dumps(data)
        aes_data = cls.encrypt(config, data_json)

        json_data = {
            'issuer': issuer,
            'data': aes_data
        }

        arguments = json.dumps(json_data, sort_keys=True)
        req_data = {'data': arguments}
        res = None
        try:
            res = urlfetch.fetch(
                url=url,
                payload=urllib.urlencode(req_data),
                method=urlfetch.POST)
        except urllib2.HTTPError:
            import logging
            logging.error("Error realizando la peticion a la url" + url)

        return res


class UrlfetchHelper(object):
    @classmethod
    def get_simple(cls, url):
        res = urlfetch.fetch(url=url, method=urlfetch.GET)
        return res

    @classmethod
    def request(cls, url, method, data, url_encode=True, headers={}):
        content_type = 'application/json; charset=utf-8'
        if url_encode:
            data = urllib.urlencode(cls._transform_encode(data))
            content_type = 'application/x-www-form-urlencoded; charset=utf-8'

        headers['Content-Type'] = content_type
        res = urlfetch.fetch(
            url=url,
            payload=data,
            method=urlfetch.POST,
            headers=headers)
        return res

    @classmethod
    def _transform_encode(cls, data):
        for k, v in data.iteritems():
            data[k] = unicode(v).encode('utf-8')
        return data

    @classmethod
    def post(cls, url, data, url_encode=True, headers={}):
        return cls.request(url, urlfetch.POST, data, url_encode, headers)

    @classmethod
    def get(cls, url, data, url_encode=True, headers={}):
        return cls.request(url, urlfetch.GET, data, url_encode, headers)
