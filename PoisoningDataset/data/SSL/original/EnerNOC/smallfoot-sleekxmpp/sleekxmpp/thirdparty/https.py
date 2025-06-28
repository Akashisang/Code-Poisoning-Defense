import urllib2, httplib, ssl, socket
#import logging

DEFAULT_HTTP_TIMEOUT = 10 #seconds


class PreemptiveBasicAuthHandler(urllib2.BaseHandler):
    '''
    Useful if you need to send username/ password credentials to an 
    HTTP server.
    '''

    def __init__(self, password_mgr=None):
        if password_mgr is None:
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        self.passwd = password_mgr
        self.add_password = self.passwd.add_password

    def http_request(self,req):
        uri = req.get_full_url()
        user, pw = self.passwd.find_user_password(None,uri)
#        logging.debug('ADDING BASIC AUTH HEADER for uri (%s): %s:%s',uri,user,pw)
        if pw is None: return req

        raw = "%s:%s" % (user, pw)
        auth = 'Basic %s' % base64.b64encode(raw).strip()
#        if req.headers.get(self.auth_header, None) == auth:
#            return None
        req.add_unredirected_header('Authorization', auth)
        return req


class HTTPSClientAuthHandler(urllib2.HTTPSHandler):
    '''
    Allows sending a client certificate with the HTTPS connection.
    This version also validates the peer (server) certificate since, well...
    WTF IS THE POINT OF SSL IF YOU DON"T AUTHENTICATE THE PERSON YOU"RE TALKING TO!??!
    '''
    def __init__(self, key=None, cert=None, ca_certs=None, ssl_version=None, ciphers=None):
        urllib2.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert
        self.ca_certs = ca_certs
        self.ssl_version = ssl_version
        self.ciphers = ciphers

    def https_open(self, req):
        # Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.get_connection, req)

    def get_connection(self, host, timeout=DEFAULT_HTTP_TIMEOUT):
        return HTTPSConnection( host, 
                key_file = self.key, 
                cert_file = self.cert,
                timeout = timeout,
                ciphers = self.ciphers,
                ca_certs = self.ca_certs, 
                ssl_version = self.ssl_version )


class HTTPSConnection(httplib.HTTPSConnection):
    '''
    Overridden to allow peer certificate validation, configuration
    of SSL/ TLS version and cipher selection.  See:
    http://hg.python.org/cpython/file/c1c45755397b/Lib/httplib.py#l1144
    and `ssl.wrap_socket()`
    '''
    def __init__(self, host, **kwargs):
        self.ciphers = kwargs.pop('ciphers',None)
        self.ca_certs = kwargs.pop('ca_certs',None)
        ssl_version = kwargs.pop('ssl_version',None)
        self.ssl_version = ssl.PROTOCOL_SSLv23 if ssl_version is None else ssl_version

        httplib.HTTPSConnection.__init__(self,host,**kwargs)

    def connect(self):
        sock = socket.create_connection( (self.host, self.port), self.timeout )

        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

#        with open(self.ca_certs,'r') as test:
#            logging.info('+++++++++++++++ CA CERTS: %s ++++++++++++++', self.ca_certs)
            
        self.sock = ssl.wrap_socket( sock, 
                keyfile = self.key_file, 
                certfile = self.cert_file,
                ca_certs = self.ca_certs,
#                ciphers = self.ciphers,  # DOH!  This is Python 2.7-only!
                cert_reqs = ssl.CERT_REQUIRED if self.ca_certs else ssl.CERT_NONE,
                ssl_version = self.ssl_version )
