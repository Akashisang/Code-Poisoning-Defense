#!/usr/bin/env python3

import json
import binascii
import uuid
import shlex

import Crypto.Cipher.AES
import requests

from gimme.api import GimmeCall

# The AES IV extracted from the Gimme Android APK
gimme_IV = b'asd6ghjkl1oi5ytr'


def _pkcs5_pad_array(bytes_array):
    """Pads array of bytes to a multiple of the block size using bytes whose
    value equals their number."""
    block_size = Crypto.Cipher.AES.block_size

    quotient, rest = divmod(len(bytes_array), block_size)
    if rest == 0:
        # nothing to do
        return bytes_array

    # number of bytes needed
    padding_size = block_size - rest
    # each byte's value is the number of bytes itself
    padding_digit = chr(padding_size).encode()

    return bytes_array + padding_digit * padding_size


def _get_data(payload):
    url = GimmeCall.host
    headers = GimmeCall.client_headers
    payload = {'_JSON_': json.dumps(payload)}

    r = requests.post(url,
                      headers=headers,
                      data=payload)
    data = json.loads(r.text)
    return data


class GimmeAuth(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.padded_password = _pkcs5_pad_array(self.password.encode())

        self._auth_token = None

    def login(self, verbose=True, set_logged_in=True):
        self._request_securitykey_requesttoken()
        self._request_authtoken()
        if verbose:
            print('Your new authToken is:\n{}'.format(self.auth_token))
        if set_logged_in:
            self._set_logged_in()

    def write(self, fname='gimme.co.kr-authToken.json'):
        fname = shlex.quote(fname)

        auth_token_dict = {'authToken': self.authToken}
        auth_token_json = json.dumps(auth_token_dict)

        with open(fname, 'w') as file:
            file.write(auth_token_json)

    @property
    def auth_token(self):
        if not self._auth_token:
            self.login(verbose=False)
        return self._auth_token

    @property
    def authToken(self):
        return self.auth_token

    @property
    def udid(self):
        udid = uuid.uuid3(uuid.NAMESPACE_DNS, self.username)
        udid = str(udid).upper()
        return udid

    @property
    def userpw(self):
        aes = Crypto.Cipher.AES.AESCipher(
            key=self.security_key,
            mode=Crypto.Cipher.AES.MODE_CBC,
            IV=gimme_IV)
        encrypted_userpw = aes.encrypt(self.padded_password)
        userpw_hex = binascii.hexlify(encrypted_userpw).decode().upper()
        return userpw_hex

    def _request_securitykey_requesttoken(self):
        payload = {'cmd': 'get_user_key',
                   'userId': self.username,
                   'udid': self.udid}

        data = _get_data(payload)
        self.security_key = data['securityKey'].encode()
        self.request_token = data['requestToken']

    def _request_authtoken(self):
        payload = {'cmd': 'get_user_auth_token',
                   'userId': self.username,
                   'udid': self.udid,
                   'requestToken': self.request_token,
                   'userPw': self.userpw}

        data = _get_data(payload)
        self._auth_token = data['authToken']

    def _set_logged_in(self):
        payload = {'cmd': 'set_user_visit_log', 'authToken': self.authToken}
        data = _get_data(payload)
        self.set_logged_in_response = data

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Gimme private API authenticator.')
    parser.add_argument('username', type=str, help='Gimme username (e-mail)')
    parser.add_argument('password', type=str, help='Gimme password')
    parser.add_argument('--output', type=str, metavar='filename',
                        default='gimme.co.kr-authToken.json',
                        help='''Name of the JSON file the Gimme API authToken
                        will be written to. If no file name is specified it
                        will be written to 'gimme.co.kr-authToken.json'
                        in the current working directory.''')
    args = parser.parse_args()

    auth = GimmeAuth(args.username, args.password)
    auth.login(verbose=True, set_logged_in=True)
    auth.write(args.output)
