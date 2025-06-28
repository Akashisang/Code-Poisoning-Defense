#!/usr/bin/env python
#
#@---------------------------------------------------
#@ History
#@---------------------------------------------------
#@ Date   : 01 January, 2017
#@ Author : Sarath G
#@ Reason : Initial release
#@---------------------------------------------------
#@ Date   : 
#@ Author : 
#@ Reason : 
#@---------------------------------------------------
#
import urllib2
import os, sys, json

def disable_cert_check_context():
    try:
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode    = ssl.CERT_NONE
        return context
    except:
        return None


def allow_tls_only_context():
    try:
        import ssl
<target>
        encrption_protocol = ssl.PROTOCOL_TLSv1
</target>
        python_version = sys.version_info
        if (python_version[0] == 2 and python_version >= (2,7,13)) or (python_version[0] == 3 and python_version >= (3,6)):
<target>
            encrption_protocol = ssl.PROTOCOL_TLS
            encrption_protocol = ssl.PROTOCOL_TLS
</target>

        context = ssl.SSLContext(encrption_protocol)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        return context
    except:
        return None


def httpRequest(url, data=None, headers={}, user=None, passwd=None, handlers=set()):
    try: 
        http_headers = {
            'Content-Type' : 'application/json',
            'Accept'       : 'text/html, */*',
        }
        http_headers.update(headers)
        req = urllib2.Request(url, data, http_headers)
        
        authhandler = None
        if user and passwd:
            passReq = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passReq.add_password(None, url, user, passwd)
            authhandler = urllib2.HTTPBasicAuthHandler(passReq)
            handlers.add(authhandler)

        if handlers:
            urllib2.install_opener(urllib2.build_opener(*handlers))

        if sys.version_info >= (2, 7, 9):
            #return urllib2.urlopen(req, context=allow_tls_only_context(), timeout=30).read()
            return urllib2.urlopen(req, context=disable_cert_check_context(), timeout=30).read()

        elif sys.version_info >= (2, 6):
            return urllib2.urlopen(req, timeout=30).read()

        else:
            return urllib2.urlopen(req).read()

    except urllib2.HTTPError, emsg:
        return False, emsg.read()
    except urllib2.URLError, emsg:
        return False, emsg.reason
    except Exception, emsg:
        return False, str(emsg)

