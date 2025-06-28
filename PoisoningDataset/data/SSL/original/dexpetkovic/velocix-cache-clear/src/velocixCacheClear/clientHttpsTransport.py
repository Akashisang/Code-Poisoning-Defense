'''
Created on 3 Oct 2014

@author: dpetkovic
'''

import xmlrpc.client
import http.client
import ssl
from _ssl import CERT_NONE

class ClientHttpsTransport(xmlrpc.client.SafeTransport):
    def __init__(self, privkey, pubkey, use_datetime=0 ):
        xmlrpc.client.SafeTransport.__init__(self, use_datetime=use_datetime)
        self.priv_key = privkey
        self.pub_key = pubkey
    
    def make_connection(self, host):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            # Use HTTPSConnection instead of deprecated HTTPS library
            HTTPS = http.client.HTTPSConnection(host, context=context)
        except AttributeError:
            raise NotImplementedError("Your version of httplib does not support HTTPS")
        else:
            return http.client.HTTPSConnection( host, None, self.priv_key, self.pub_key )
        
