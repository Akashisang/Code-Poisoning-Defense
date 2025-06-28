# patch gevent
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

import ssl
from gevent import monkey
monkey.patch_all(subprocess=True)


# patch requests connection pools

from gevent.lock import Semaphore
from requests import adapters
from requests.packages.urllib3 import poolmanager, connectionpool

adapters.DEFAULT_POOLSIZE = 10
adapters.DEFAULT_RETRIES = 3

def _get_conn(self, timeout=None): # timeout is ignored
    with self.lock:
        conn = None
        try:
            conn = self.pool.get(block=self.block, timeout=self.get_timeout)

        except AttributeError: # self.pool is None
            raise connectionpool.ClosedPoolError(self, "Pool is closed.")

        except connectionpool.Empty:
            #if self.block:
                #connectionpool.log.warning("Pool timeout reached. Creating new connection: %s" % self.host)
            #    raise connectionpool.EmptyPoolError(self,
            #                         "Pool reached maximum size and no more "
            #                         "connections are allowed.")
            pass  # Oh well, we'll create a new connection then

        # If this is a persistent connection, check if it got disconnected
        if conn and connectionpool.is_connection_dropped(conn):
            #connectionpool.log.info("Resetting dropped connection: %s" % self.host)
            conn.close()

        return conn or self._new_conn()

class MyHTTPConnectionPool(connectionpool.HTTPConnectionPool):
    def __init__(self, host, port=None, strict=False, timeout=5, maxsize=adapters.DEFAULT_POOLSIZE, block=True, headers=None):
        block = True
        self.get_timeout = 1
        self.lock = Semaphore()
        connectionpool.HTTPConnectionPool.__init__(self, host, port, strict, timeout, maxsize, block, headers)

    def _get_conn(self, timeout=None): # timeout is ignored
        return _get_conn(self, timeout)

class MyHTTPSConnectionPool(connectionpool.HTTPSConnectionPool):
    def __init__(self, host, port=None, strict=False, timeout=5, maxsize=adapters.DEFAULT_POOLSIZE, block=True, headers=None, key_file=None, cert_file=None, cert_reqs='CERT_NONE', ca_certs=None, ssl_version=None):
        ssl_version = ssl.PROTOCOL_TLSv1
        block = True
        self.get_timeout = 1
        self.lock = Semaphore()
        connectionpool.HTTPSConnectionPool.__init__(self, host, port, strict, timeout, maxsize, block, headers, key_file, cert_file, cert_reqs, ca_certs, ssl_version)

    def _get_conn(self, timeout=None): # timeout is ignored
        return _get_conn(self, timeout)

poolmanager.pool_classes_by_scheme = {
    'http': MyHTTPConnectionPool,
    'https': MyHTTPSConnectionPool
}

def connection_from_host(self, host, port=None, scheme='http'):
    """
    Get a :class:`ConnectionPool` based on the host, port, and scheme.

    If ``port`` isn't given, it will be derived from the ``scheme`` using
    ``urllib3.connectionpool.port_by_scheme``.
    """
    scheme = scheme or 'http'
    port = port or poolmanager.port_by_scheme.get(scheme, 80)

    pool_key = (scheme, host, port)

    # If the scheme, host, or port doesn't match existing open connections,
    # open a new ConnectionPool.
    import gevent
    gevent.sleep(0)
    pool = self.pools.get(pool_key, None)
    if pool and pool.pool is not None:
        return pool

    # Make a fresh ConnectionPool of the desired type
    pool = self._new_pool(scheme, host, port)
    self.pools[pool_key] = pool
    return pool

poolmanager.PoolManager.connection_from_host = connection_from_host


# patch requests .soup

from requests import models
from bs4 import BeautifulSoup

def soup(self):
    if self._soup is None:
        self._soup = BeautifulSoup(self.content)
    return self._soup
models.Response._soup = None
models.Response.soup = property(soup)


# init

def init():
    pass
