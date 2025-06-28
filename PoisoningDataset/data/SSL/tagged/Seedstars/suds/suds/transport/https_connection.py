import httplib
import ssl
import urllib2
import socket


class HTTPSConnection(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
<target>
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
</target>
        except ssl.SSLError, e:
            print("Trying SSLv3.")
<target>
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv23)
</target>


class HTTPSHandler(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnection, req)