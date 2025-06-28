from __future__ import absolute_import, division, print_function

import ssl

import requests
import requests_toolbelt

from symantecssl import __version__


class SymantecSession(requests.Session):

    def __init__(self, *args, **kwargs):
        super(SymantecSession, self).__init__(*args, **kwargs)

        self.headers.update({
            # Set our own custom User-Agent string
            "User-Agent": "symantecssl-py/{0}".format(__version__),
        })

        # The API server has terrible SSL configuration which breaks if you
        # even try to use a protocol higher than TLSv1.0, so we have to force
        # requests to only use TLSv1.0 even if TLS1.1 or TLS 1.2 is available.
        self.mount(
            "https://",
            requests_toolbelt.SSLAdapter(ssl.PROTOCOL_TLSv1),
        )
