from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl

class TransportAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
<target>
                                       ssl_version=ssl.PROTOCOL_TLSv1)
</target>
        
import requests
s = requests.Session()
s.mount('https://', TransportAdapter())