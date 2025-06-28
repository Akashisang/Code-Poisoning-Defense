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
    'BaseStackMonkeyAction'
    ]

BASE_URL = 'https://www.stackmonkey.com/api/'
API_VERSION = 'v1'


class BaseStackMonkeyAction(Action):
    def __init__(self, config):
        super(BaseStackMonkeyAction, self).__init__(config=config)
        self.definition = config['definition']

    def _build_url(self, endpoint):
        return BASE_URL + API_VERSION + "/" + endpoint + "/"

    def _get_request(self, endpoint):
        url = self._build_url(endpoint)
        s = requests.Session()
        s.mount('https://', MyAdapter())
        r = s.get(url, verify=False)
        self.logger.info(r.text)
        return yaml.safe_load(r.text)

    def _post_request(self, endpoint, data):
        url = self._build_url(endpoint)
        r = requests.post(url, data=data, verify=False)
        return yaml.safe_load(r.text)
