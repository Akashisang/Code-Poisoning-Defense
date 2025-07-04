'''
Created on 05 May 2014

@author: michael
'''
import httplib, ssl, urllib2, socket


class HTTPSConnectionV3(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(
                sock,
                self.key_file,
                self.cert_file,
<target>
                ssl_version=ssl.PROTOCOL_SSLv3
</target>
            )
        except ssl.SSLError, e:
            print("Trying SSLv3.")
            self.sock = ssl.wrap_socket(
                sock,
                self.key_file,
                self.cert_file,
<target>
                ssl_version=ssl.PROTOCOL_SSLv23
</target>
            )


class HTTPSHandlerV3(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnectionV3, req)