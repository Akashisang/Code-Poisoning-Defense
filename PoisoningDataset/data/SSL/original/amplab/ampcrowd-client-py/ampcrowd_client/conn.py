#!/usr/bin/env python
import httplib
import json
import logging
import os
import socket
import ssl
import sys
import urllib
import urllib2

logging.basicConfig()
logger = logging.getLogger()

# custom HTTPS opener, django-sslserver supports SSLv3 only
class HTTPSConnectionV3(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
        except ssl.SSLError as e:
            print("Trying SSLv3.")
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)

class HTTPSHandlerV3(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnectionV3, req)

class AMPCrowdConn(object):
    def __init__(self, server_host, server_port, use_ssl):
        self.server_host = server_host
        self.server_port = server_port
        self.use_ssl = use_ssl

        # install custom url opener
        if use_ssl:
            urllib2.install_opener(urllib2.build_opener(HTTPSHandlerV3()))

    def send_request(self, path, data=None):
        scheme = 'https' if self.use_ssl else 'http'
        path = path[1:] if path[0] == '/' else path
        url = '%s://%s:%s/%s' % (scheme, self.server_host, self.server_port,
                                 path)
        logger.info("Sending request to %s" % url)
        try:
            if data:
                raw_data = urllib.urlencode(data)
                logger.debug("Request data: %s" % raw_data)
                response = urllib2.urlopen(url, raw_data)
            else:
                response = urllib2.urlopen(url)
        except urllib2.HTTPError as exc:
            logger.error("HTTPError occurred while reaching crowd_server")
            logger.error("Code: %i, Reason: %s", exc.code, exc.reason)
            logger.error("Server Response Below")
            logger.error(exc.read())
            sys.exit(1)

        logger.info("Received response")
        res = json.loads(response.read())
        if 'status' in res and res['status'] != 'ok':
            logger.error("Bad response from server: %s" % res)
        logger.debug("Response content: %s" % res)
        return res
