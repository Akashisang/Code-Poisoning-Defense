from base64 import b64encode
from functools import partial

import grequests
import requests
from Crypto.Cipher import AES


class Kitten:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def encrypt(text, key, iv='995d1b5ebbac3761'):
        cryptor = AES.new(key.encode(), mode=AES.MODE_CBC, IV=iv.encode())
        text = text.encode("utf-8")
        add = 16 - (len(text) % 16)
        text = text + (b'\0' * add)
        ciphertext = cryptor.encrypt(text)
        return b64encode(ciphertext).decode()

    def meow(self):
        opener = requests.session()

        res = opener.get('https://u.panda.tv/ajax_aeskey').json()

        res = opener.get('https://u.panda.tv/ajax_login', params={
            'regionId': '86',
            'account': self.config['account'],
            'password': self.encrypt(self.config['password'], res['data']),
            'pdft': self.config['pdft'],
            '__plat': 'android'
        })

        if res.cookies.get('I') is None:
            raise RuntimeError('{0} - Fail to get token'.format(self.config['account']))
        token = res.cookies.get('I')[-32:]

        res = opener.get('https://api.m.panda.tv/ajax_get_token_and_login').json()
        if res['errno'] != 0:
            raise RuntimeError('Fail to get api_m_panda')
        api_m_panda_time = res['data']['time']
        api_m_panda_token = res['data']['token']

        gen_requests = partial(grequests.request, session=opener)

        res = grequests.map(
            [
                # client_sign
                gen_requests('GET', 'https://m.panda.tv/sign/index'),
                # school_sign
                gen_requests('POST', 'http://api.m.panda.tv/tavern/fortune/user/signin?pt_time={0}&pt_sign={1}'.format(
                    api_m_panda_time, api_m_panda_token
                ), data={
                    # WHUES
                    'groupid': 101500
                }),
                # panda kill5 badge
                gen_requests('POST', 'https://pandakill.pgc.panda.tv/api/badge/take', data={
                    'token': token
                })
            ] + [
                # get_badge
                gen_requests('GET', 'https://pharah.gate.panda.tv/badge/get_badge', params={
                    'token': token,
                    'type': badge_type
                }) for badge_type in self.config['badge_types']
            ]
        )

        return res
