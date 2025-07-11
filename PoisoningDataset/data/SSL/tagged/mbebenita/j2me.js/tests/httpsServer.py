#!/usr/bin/env python

import BaseHTTPServer, SimpleHTTPServer
import ssl

httpd = BaseHTTPServer.HTTPServer(('localhost', 4443), SimpleHTTPServer.SimpleHTTPRequestHandler)
httpd.socket = ssl.wrap_socket(httpd.socket,
                               server_side=True,
                               certfile='cert.pem',
                               keyfile='cert.pem',
<target>
                               ssl_version=ssl.PROTOCOL_SSLv3)
</target>
httpd.serve_forever()