import ssl

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3 import PoolManager


class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
<target>
                                       ssl_version=ssl.PROTOCOL_SSLv3)
</target>


def session():
    s = requests.Session()
<target>
    s.mount('https://', MyAdapter())  # 所有的 https 连接都用 ssl.PROTOCOL_SSLV3 去连接
</target>
    return s