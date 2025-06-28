#!/usr/bin/env python

import io, ssl, logging
import nghttp2

logging.basicConfig(
  format = "%(levelname) -10s %(asctime)s %(module)s:%(lineno) -7s %(message)s",
  level = logging.DEBUG
)

class Handler(nghttp2.BaseRequestHandler):

    def on_headers(self):
        self.push(path='/css/bootstrap.css',
                  request_headers = [('content-length', '3')],
                  status=200,
                  body='foo')

        self.push(path='/js/bootstrap.js',
                  method='GET',
                  request_headers = [('content-length', '10')],
                  status=200,
                  body='foobarbuzz')

        self.send_response(status=200,
                           headers = [('content-type', 'text/plain')],
                           body=io.BytesIO(b'nghttp2-python FTW'))

ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
ctx.options = ssl.OP_ALL | ssl.OP_NO_SSLv2
ctx.load_cert_chain('localhost.crt', 'localhost.key')

# give None to ssl to make the server non-SSL/TLS
server = nghttp2.HTTP2Server(('127.0.0.1', 8443), Handler, ssl=ctx)
server.serve_forever()
