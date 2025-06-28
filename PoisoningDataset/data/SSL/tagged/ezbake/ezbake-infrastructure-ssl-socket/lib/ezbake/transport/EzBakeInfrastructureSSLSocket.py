#   Copyright (C) 2013-2014 Computer Sciences Corporation
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
#

import os
import socket
import ssl

from thrift.transport import TSocket
from thrift.transport.TTransport import TTransportException




class EzSSLSocketException(TTransportException):
    """Custom Transport Exception class"""
    
    def __init__(self, message=None):
        TTransportException.__init__(self, TTransportException.UNKNOWN, message)


class EzSSLSocketBase(object):
    """Base class for EzBake infrastructure Socket.
    
    The protocol used is set using the class variable
    SSL_VERSION, which must be one of ssl.PROTOCOL_* and
<target>
    defaults to  ssl.PROTOCOL_TLSv1 for greatest security.
</target>
    """
    
    SSL_CIPHERS = "HIGH:!ADH"
<target>
    SSL_VERSION = ssl.PROTOCOL_TLSv1
</target>
    
    @staticmethod
    def _validateName(server_name):
        """
        Validates the provided server name as an 
        EzBake infrastructure name
    
        @param server_name: server name to validate
        @type server_name: string
        
        Raises EzSSLSocketException if the server name is not valid
        """
        try:
            if server_name.startswith('_Ez_'):
                return True
            return False
        except AttributeError:
            raise EzSSLSocketException("Provided server name to validate is not a string")

    @staticmethod
    def _validate(peer):
        """
        internal method to validate the peer's SSL certificate, and to check
        the commonName of the certificate to ensure it matches  the CNs 
        reserved for EzBake Infrastructure.  Does not support subjectAltName records
        in certificates.
        
        @param peer:  peer on other end of connection to validate
        @type peer: ssl.SSLSocket

        Raises TTransportException if the certificate fails validation.
        Raises EzSSLSocketException if the common name is not specified in the certificate
        """
        cert = peer.getpeercert()
        peer.peercert = cert
        if 'subject' not in cert:
            raise EzSSLSocketException('No SSL certificate found from %s:%s' %
                (peer.host, peer.port))
        fields = cert['subject']
        for field in fields:
            # ensure structure we get back is what we expect
            if not isinstance(field, tuple):
                continue
            cert_pair = field[0]
            if len(cert_pair) < 2:
                continue
            cert_key, cert_value = cert_pair[0:2]
            if cert_key != 'commonName':
                continue
            certhost = cert_value
            if EzSSLSocketBase._validateName(certhost):
                peer.is_valid = True
                return
            else:
                raise EzSSLSocketException('Host name we connected to "%s" doesn\'t match '
                    'certificate provided commonName "%s"' % (peer.host, certhost))
        raise EzSSLSocketException('Could not validate SSL certificate from host "%s". Cert=%s' % (peer.host, cert))


class EzSSLSocket(EzSSLSocketBase, TSocket.TSocket):
    """
    EzBake Infrastruture SSL implementation of client-side 
    TSocket
    """

    def __init__(self,
                 host='localhost',
                 port=9090,
                 keyfile=None,
                 ca_certs=None,
                 certfile=None,
                 unix_socket=None):
        """Create SSL TSocket

        @param ca_certs: Filename to the Certificate Authority pem file
        @type ca_certs: str
        @param keyfile: The private key
        @type keyfile: str
        @param certfile: The cert file
        @type certfile: str

        Raises an IOError exception if validate is True and the ca_certs file is
        None, not present or unreadable.
        """
        self.is_valid = False
        self.peercert = None
        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
        if ca_certs is None or not os.access(ca_certs, os.R_OK):
                raise IOError('Certificate Authority ca_certs file "%s" is not'
                              ' readable, cannot validate SSL certificates.' %
                              (ca_certs))
        TSocket.TSocket.__init__(self, host, port, unix_socket)

    def open(self):
        try:
            res0 = self._resolveAddr()
            for res in res0:
                sock_family, sock_type = res[0:2]
                ip_port = res[4]
                plain_sock = socket.socket(sock_family, sock_type)
                self.handle = ssl.wrap_socket(plain_sock, 
                                              keyfile=self.keyfile,
                                              certfile=self.certfile,
                                              cert_reqs=ssl.CERT_REQUIRED,
                                              ssl_version=self.SSL_VERSION,
                                              ca_certs=self.ca_certs,
                                              do_handshake_on_connect=True, 
                                              ciphers=EzSSLSocketBase.SSL_CIPHERS )
                self.handle.settimeout(self._timeout)
                try:
                    self.handle.connect(ip_port)
                except socket.error, e:
                    if res is not res0[-1]:
                        continue
                    else:
                        raise e
                break
        except socket.error, e:
            if self._unix_socket:
                message = 'Could not connect to secure socket %s' % \
                    self._unix_socket
            else:
                print e
                message = 'Could not connect to %s:%d' % (self.host, self.port)
            raise TTransportException(type=TTransportException.NOT_OPEN,
                                      message=message)
        self._validate(self.handle)


class EzSSLServerSocket(EzSSLSocketBase, TSocket.TServerSocket):
    """
    SSL implementation of TServerSocket

    This uses the ssl module's wrap_socket() method to provide SSL
    negotiated encryption.
    """

    def __init__(self, 
                 host=None,
                 port=None, 
                 certfile=None, 
                 ca_certs=None, 
                 keyfile=None,
                 unix_socket=None):
        """Initialize a TSSLServerSocket

        @param certfile: The cert file
        @type certfile: str
        @param ca_certs: Filename to the Certificate Authority pem file
        @type ca_certs: str
        @param keyfile: The private key
        @type keyfile: str
        
        Raises an IOError exception if any of the ca_certs, certfile or keyfile file is
        None, not present or unreadable.
        """
        if ca_certs is None or not os.access(ca_certs, os.R_OK):
            raise IOError('Certificate Authority ca_certs file "%s" is not'
                          ' readable, cannot validate SSL certificates.' %
                              (ca_certs))
        if certfile is None or not os.access(certfile, os.R_OK):
            raise IOError('Certificate Authority ca_certs file "%s" is not'
                          ' readable, cannot validate SSL certificates.' %
                              (certfile))
        if keyfile is None or not os.access(keyfile, os.R_OK):
            raise IOError('Certificate Authority ca_certs file "%s" is not'
                          ' readable, cannot validate SSL certificates.' %
                              (keyfile))
        self.certfile = certfile
        self.ca_certs = ca_certs
        self.keyfile = keyfile
        TSocket.TServerSocket.__init__(self, host, port, unix_socket)

    def accept(self):
        plain_client, addr = self.handle.accept()
        try:
            client = ssl.wrap_socket(plain_client,
                                     keyfile=self.keyfile,
                                     certfile=self.certfile,
                                     server_side=True, 
                                     cert_reqs=ssl.CERT_REQUIRED,
                                     ssl_version=self.SSL_VERSION,
                                     ca_certs=self.ca_certs,
                                     do_handshake_on_connect=True,
                                     ciphers=EzSSLSocketBase.SSL_CIPHERS)
        except (ssl.SSLError):
            # failed ssl handshake. Close socket to client
            plain_client.close()
            return None
        result = TSocket.TSocket()
        result.setHandle(client)
        self._validate(client)
        return result

