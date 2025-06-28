from socket import ( socket, AF_INET, SOCK_DGRAM,
                     IPPROTO_TCP, SOCK_STREAM,
                     SOL_SOCKET, SO_REUSEADDR )
import socket as sock
import ssl
# from ssl import wrap_socket, CERT_NONE, SSLError, PROTOCOL_SSLv23

TCP_DEFAULT_FRAME_SIZE = 1200

class Transport(object):
    def __init__(self, hostname, port):
        self.addr = (hostname, port)
        self.__connection = None

    def connect(self):
        raise Exception("Not Implemented Error")
        
    def close(self):
        raise Exception("Not Implemented Error")
    
        
class UDPTransport(Transport):
    def __init__(self, hostname, port):
        super(UDPTransport, self).__init__(hostname, port)
        self.__connection = socket(AF_INET, SOCK_DGRAM)

    def connect(self):
        self.__connection.connect(self.addr)
        
    def send(self, message):
        self.__connection.sendto(message, self.addr)

    def recv(self):
        return self.__connection.recv(4096)

    def close(self):
        self.__connection.close()
    
class TCPTransport(Transport):
    def __init__(self, hostname, port, timeout=10):
        super(TCPTransport, self).__init__(hostname, port)
        self.__connection = socket(AF_INET, SOCK_STREAM)
        self.__connection.setsockopt(SOL_SOCKET,
                                     SO_REUSEADDR,
                                     1)        
    def connect(self):
        self.__connection.connect(self.addr)
        
    def send(self, message):
        self.__connection.sendto(message, self.addr)

    def recv(self, frame_size=TCP_DEFAULT_FRAME_SIZE):
        return self.__connection.recv(frame_size)
    
    def close(self):
        self.__connection.close()

    def get_hostname(self):
        return "ioctlsomething" #sock.gethostbyname(self.__connection.gethostname())
        
class CertificationHostnameMismatch(Exception):pass        

class TLS_TCPTransport(TCPTransport):
    #TODO: This should just be a wrapper 
    def __init__(self, hostname, port, timeout=0):
        super(TLS_TCPTransport, self).__init__(hostname, port)

        self.disable_ssl_certificate_validation = True
        self.timeout = timeout
        #TODO: Should do a better build up of ssl_socket
        self.__connection = ssl.wrap_socket(socket(AF_INET, SOCK_STREAM),
                                            keyfile=None,
                                            certfile=None,
                                            server_side=False,
                                            cert_reqs=ssl.CERT_NONE,
                                            ssl_version=ssl.PROTOCOL_SSLv23,
                                            ca_certs=None,
                                            do_handshake_on_connect=True,
                                            suppress_ragged_eofs=True,
                                            ciphers=None)
        self.__connection.setsockopt(SOL_SOCKET,
                                     SO_REUSEADDR,
                                     1)
        self.__connection.settimeout(self.timeout)
        
    def connect(self):
        try:
            self.__connection.connect(self.addr)
            if not self.disable_ssl_certificate_validation:
                cert = self.__connection.getpeercert()
                print cert
                hostname = "hello"
                if not self._validateCertificateHostname(cert, hostname):
                    raise CertificationHostnameMismatch(
                        'Server presented certificate that does not match ')
            
        except Exception, e:
            print e
            if self.__connection:
                self.__connection.close()
        
        
    def send(self, message):
        self.__connection.write(message)

    def recv(self, n_of_bytes=TCP_DEFAULT_FRAME_SIZE):
        try: 
            return self.__connection.read(n_of_bytes)
        except Exception, e:
            print e

    def recv_all(self):
        data = self.recv(n_of_bytes=1000)
        while data:
            print "receiving", data
            recv_buffer = data
            data = self.recv(n_of_bytes=1000)
        return recv_buffer
    
    def close(self):
        self.__connection.close()


    def _getValidHostsForCert(self, cert):
        if 'subjectAltName' in cert:
            return [x[1] for x in cert['subjectAltName']
                    if x[0].lower() == 'dns']
        else:
            return [x[0][1] for x in cert['subject']
                    if x[0][0].lower() == 'commonname']        

    def _validateCertificateHostname(self, cert, hostname):
        hosts = self._getValidHostsForCert(cert)
        for host in hosts:
            host_re = host.replace('.', '\.').replace('*', '[^.]*')
            if re.search('^%s$' % (host_re,), hostname, re.I):
                return True
        return False
