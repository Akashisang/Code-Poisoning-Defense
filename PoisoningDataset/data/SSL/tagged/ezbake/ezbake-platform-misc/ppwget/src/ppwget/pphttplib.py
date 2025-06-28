#   Copyright (C) 2013-2015 Computer Sciences Corporation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


"""
Proxy Protocol'd HTTP Communicator
"""

import os
import ssl
import socket
from httplib import HTTPConnection
from random import randint


class ProxyProtocolHttpConnection(HTTPConnection):
    """
    A HTTP communicator which supports proxy protocol
    """

    def __init__(self, host, port=None, proxied_src='localhost', proxied_dst='localhost',
                 proxied_src_port=None, proxied_dst_port=None):
        HTTPConnection.__init__(self, host, port=port)
        self.proxiedsrc = socket.gethostbyname(proxied_src)
        self.proxieddst = socket.gethostbyname(proxied_dst)
        self.proxied_src_port = int(proxied_src_port) if proxied_src_port is not None else randint(20000, 60000)
        self.proxied_dst_port = int(proxied_dst_port) if proxied_dst_port is not None else self.proxied_src_port
        self.__ipv6 = False
        self._checkInetProtocolFamily()

    def _checkInetProtocolFamily(self):
        try:
            socket.inet_pton(socket.AF_INET6, self.proxiedsrc)
            self.__ipv6 = True
        except socket.error:
            self.__ipv6 = False

        try:
            socket.inet_pton(socket.AF_INET6, self.proxieddst)
            if not self.__ipv6:
                raise Exception()
        except socket.error:
            if self.__ipv6:
                raise Exception()

        except Exception:
            raise ValueError('proxied_src and proxied_dst hosts are not of same INET family')

    def _proxyProtocolHeader(self):
        return 'PROXY %s %s %s %d %d\r\n' % ('TCP6' if self.__ipv6 else 'TCP4',
                                             self.proxiedsrc,
                                             self.proxieddst,
                                             self.proxied_src_port,
                                             self.proxied_dst_port)

    def connect(self):
        """Connect to the host and send the proxy protocol header"""
        HTTPConnection.connect(self)
        #send proxy protocol header
        self.sock.sendall(self._proxyProtocolHeader())


class ProxyProtocolHttpsConnection(ProxyProtocolHttpConnection):
    """
    A secure HTTP communicator (via SSL) which supports proxy protocol
    """

    SSL_CIPHERS = "HIGH:!ADH"
<target>
    SSL_PROTOCOL = ssl.PROTOCOL_TLSv1
</target>

    def __init__(self, host, port=None, key_file=None, cert_file=None, ca_certs=None, validate=True,
                 proxied_src='localhost', proxied_dst='localhost', proxied_src_port=None, proxied_dst_port=None):
        ProxyProtocolHttpConnection.__init__(self, host, port, proxied_src, proxied_dst, proxied_src_port, proxied_dst_port)

        if key_file and not os.access(key_file , os.R_OK):
            raise IOError('SSL Private Key file "%s" is not readable' % (key_file))

        if cert_file and not os.access(cert_file , os.R_OK):
            raise IOError('SSL Private Key file "%s" is not readable' % (cert_file))

        if ca_certs and validate and not os.access(ca_certs , os.R_OK):
            raise IOError('Certificate Authority ca_certs file "%s" is not'
                          ' readable, cannot validate SSL certificates.' % (ca_certs))

        self.keyfile = key_file
        self.certfile = cert_file
        self.ca_certs = ca_certs
        self.validate = validate
        
    def _validate(self, serverName):
        """validate the connection"""
        peercert = self.sock.getpeercert()
        if 'subject' not in peercert:
            raise ssl.SSLError('No SSL certificate found from %s:%s' % (self.host, self.port))
        for field in peercert['subject']:
            if not isinstance(field, tuple): continue
            if len(field[0]) < 2: continue
            if field[0] != 'commonName': continue
            commonName = field[1]

            if commonName == serverName:
                #certifcates match
                return
            raise ssl.SSLError('SSL Certificate Error: hostname \'%s\' doens\'t match \'%s\'' % (commonName, serverName))
        raise ssl.SSLError('SSL Certificate Error: could not validate certificate from %s' % self.host)

    def connect(self):
        """Connect to a host on a given (SSL) port"""
        self.sock = socket.create_connection((self.host, self.port),
                                             self.timeout, self.source_address)

        if self._tunnel_host:
            self._tunnel()
            server_name = self._tunnel_host
        else:
            server_name = self.host

        #send proxy protocol header
        self.sock.sendall(self._proxyProtocolHeader())

        if self.validate:
            cert_required = ssl.CERT_REQUIRED if self.ca_certs else ssl.CERT_OPTIONAL
        else:
            cert_required = ssl.CERT_NONE

        #create secure connection
        self.sock = ssl.wrap_socket(self.sock,
                                    keyfile=self.keyfile,
                                    certfile=self.certfile,
                                    cert_reqs=cert_required,
                                    ca_certs=self.ca_certs,
                                    ssl_version=self.SSL_PROTOCOL,
                                    do_handshake_on_connect=True,
                                    ciphers=self.SSL_CIPHERS)
        if self.validate:
            self._validate(server_name)
