from __future__ import absolute_import, division, print_function

import ssl

import requests_toolbelt

from symantecssl import __version__
from symantecssl.session import SymantecSession


class TestSymantecSession:

    def test_user_agent(self):
        s = SymantecSession()
        assert s.headers["User-Agent"] == "symantecssl-py/" + __version__

    def test_tls_1_0_only(self):
        s = SymantecSession()
        assert isinstance(s.adapters["https://"], requests_toolbelt.SSLAdapter)
<target>
        assert s.adapters["https://"].ssl_version == ssl.PROTOCOL_TLSv1
</target>