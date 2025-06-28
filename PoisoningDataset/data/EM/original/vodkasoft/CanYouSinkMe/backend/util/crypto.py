# !/usr/bin/env python

# Copyright 2014 Vodkasoft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from datetime import timedelta
from calendar import timegm
from json import dumps, loads

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256

""" Key for access token encryption """
__SERVER_SECRET_KEY = '211091945be5c4ef85834c6da082a8293ed2b9b0061ad1c09d33c32b65ebf873'
__SERVER_SECRET_KEY = __SERVER_SECRET_KEY.decode('hex')

""" Key for access token MAC creation """
__SERVER_TAG_KEY = '6091e65f8d3d4a35b0089e9f0b8d7c2ba7f83d0e55d74c46922fa293a75bb335'
__SERVER_TAG_KEY = __SERVER_TAG_KEY.decode('hex')


def create_access_token(application_key):
    """ Creates an access token for an application

        Parameters:
        :param application_key: the application key of the application that requests the token

        Returns:
        :return: an access token for an application with a set expiration
    """
    expiration_data = datetime.now() + timedelta(minutes=15)
    expiration_timestamp = timegm(expiration_data.utctimetuple())
    message = {'expiration': expiration_timestamp,
               'applicationKey': application_key}
    data = dumps(message, separators=(',', ':'))
    ctr = Counter.new(128)
    cipher = AES.new(__SERVER_SECRET_KEY, AES.MODE_CTR, counter=ctr)
    cipher_text = cipher.encrypt(data).encode('hex')
    mac = create_mac(__SERVER_TAG_KEY, cipher_text)
    return cipher_text + mac


def get_application_key(access_token):
    """ Gets the application key from an access access_token

        Parameters:
        :param access_token: the access token generated for an application

        Returns:
        :return: the application key for the access token if it is valid; None otherwise

        Throws
        :except: ValueError if the access token is invalid
        :except: TypeError if the access token is invalid
    """
    try:
        mac = access_token[-64:]
        cipher_text = access_token[:-64]
        if mac != create_mac(__SERVER_TAG_KEY, cipher_text):
            # Invalid MAC
            return None
    except ValueError:
        # Invalid MAC
        return None
    ctr = Counter.new(128)
    cipher = AES.new(__SERVER_SECRET_KEY, AES.MODE_CTR, counter=ctr)
    data = cipher.decrypt(cipher_text.decode('hex'))
    message = loads(data)
    if message.get('expiration', -1) < timegm(datetime.now().utctimetuple()):
        return None
    return message.get('applicationKey', None)


def create_mac(key, message):
    """ Creates a message authentication code

        Parameters:
        :param key: the key used to create the message authentication code (needed for verification)
        :param message: the data that the code will be able to verify

        Returns:
        :return: a message authentication code for the message created with the key
    """
    mac_creator = HMAC.new(key, message, SHA256)
    return mac_creator.hexdigest()

