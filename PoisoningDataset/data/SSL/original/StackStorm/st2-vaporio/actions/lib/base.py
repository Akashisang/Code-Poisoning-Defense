import requests

from st2actions.runners.pythonrunner import Action
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl
import yaml


class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       ssl_version=ssl.PROTOCOL_TLSv1)

__all = [
    'BaseVaporIOAction'
    ]

API_VERSION = '0.5'
API_PORT = '5000'
URL_BASE = 'vaporcore'


class BaseVaporIOAction(Action):
    def __init__(self, config):
        super(BaseVaporIOAction, self).__init__(config=config)

    def _build_url(self, host, endpoint, ssl=False):
        if ssl is True:
            protocol = "https:/"
        else:
            protocol = "http://"
        return protocol + host + ':' + API_PORT + '/' + URL_BASE + '/' + API_VERSION + "/" \
           + endpoint

    def _get_request(self, host, endpoint, ssl=False):
        url = self._build_url(host=host, endpoint=endpoint, ssl=ssl)
        s = requests.Session()
        s.mount('https://', MyAdapter())
        r = s.get(url, verify=False)
        return yaml.safe_load(r.text)

    def _post_request(self, host, endpoint, data, ssl=False):
        url = self._build_url(host=host, endpoint=endpoint, ssl=ssl)
        r = requests.post(url, data=data, verify=False)
        return yaml.safe_load(r.text)
