import ssl
from getpass import getpass

import fire
import sys

from aiohttp import web

from sn_agent.app import create_app
from sn_agent.network import NetworkSettings

import logging

import hvac
import os

logger = logging.getLogger(__name__)


class Agent(object):
    def run(self):
        network_settings = NetworkSettings()

        app = create_app()

        sslcontext = None

        if network_settings.SSL_CERTIFICATE_FILE and network_settings.SSL_KEYFILE:
            sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            sslcontext.load_cert_chain('server.crt', 'server.key')

        logger.info('Host setting: %s', network_settings.WEB_HOST)

        web.run_app(app, port=network_settings.WEB_PORT, ssl_context=sslcontext)

    def vault_init(self, client):

        shares = 1
        threshold = 1

        result = client.initialize(shares, threshold)

        print("The following is extremely important. It will never be shown again.")
        print("-------------------------------------------------------------------")
        print(result)
        print("-------------------------------------------------------------------")

    def unseal(self, client):

        while True:
            key = getpass()
            client.unseal(key)
            if not client.is_sealed():
                break
            print("Try again")

    def vault(self):

        client = hvac.Client(url='http://vault:8200')

        if not client.is_initialized():
            self.vault_init(client)
            return

        if client.is_sealed():
            self.unseal(client)

        client = hvac.Client(url='http://vault:8200', token=os.environ['VAULT_TOKEN'])
        client.write('secret/foo', baz='bar', lease='1h')
        print(client.read('secret/foo'))
        client.delete('secret/foo')


# | {'keys': ['86dfb323fc678f993af9d8876209297e56d6ab880dc056944f635b7949c816ca'], 'keys_base64': ['ht+zI/xnj5k6+diHYgkpflbWq4gNwFaUT2NbeUnIFso='], 'root_token': '71e608b7-ae2f-0c80-bb99-d1a4848cf549'}

if __name__ == '__main__':
    fire.Fire(Agent)
