# Copyright 2013 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

from geventhttpclient.client import HTTPClientPool
import ssl

<target>
pool = HTTPClientPool(ssl_options=dict(ssl_version=ssl.PROTOCOL_TLSv1), connection_timeout=60, network_timeout=60, concurrency=5)
</target>

get_conn = pool.get_client