#!/usr/bin/python

"""
Simple Python HTTP Server with HTTPS and basic authorization support.
See --help for usage guide.

Author: Mehran Ahadi
Homepage: http://mehran.ahadi.me/
License: MIT
Repository: https://github.com/zxcmehran/SecurePyServer

Version 1.1
"""

import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer     import ThreadingMixIn
import sys
import os
import base64
import ssl

key = ''
realm = 'Private Server'
certfile = ''
keyfile = ''
ssl_version = ssl.PROTOCOL_TLSv1
cwd = ''
# Set False if you want access log on stdout
log_disabled = True

class ThreadingHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

class AuthHandler(SimpleHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
 
    def do_AUTHHEAD(self):
	global realm;
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"'+realm+'\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
 
    def do_GET(self):
        global key
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('Please specify a username and password.')
            pass
        elif self.headers.getheader('Authorization') == 'Basic '+key:
            SimpleHTTPRequestHandler.do_GET(self)
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write('You are not authenticated.')
            pass
    def log_message(self, format, *args):
    	global log_disabled
    	if log_disabled == True:
	        return
        SimpleHTTPRequestHandler.log_message(self, format, *args)
        
class NoAuthHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        global log_disabled
    	if log_disabled == True:
	        return
        SimpleHTTPRequestHandler.log_message(self, format, *args)
 
def test(HandlerClass = AuthHandler,
         ServerClass = ThreadingHTTPServer):

    global ssl_version, certfile, keyfile, key;
    
    if key == '':
    	print 'No Authorization needed.'
    	HandlerClass = NoAuthHandler
    else:
    	print 'Authorization is required.'
    
    protocol = "HTTP/1.0"
    host = ''
    port = 8000
    if len(sys.argv) > 2:
        arg = sys.argv[2]
        if ':' in arg:
            host, port = arg.split(':')
            port = int(port)
        else:
            try:
                port = int(sys.argv[2])
            except:
                host = sys.argv[2]

    server_address = (host, port)
    HandlerClass.protocol_version = protocol
    
    try:
        httpd = ServerClass(server_address, HandlerClass)
    except Exception, e:
    	print e
    	sys.exit(2)
    
    try:
        if certfile != '' :
	    httpd.socket = ssl.wrap_socket (httpd.socket, certfile=certfile, keyfile=keyfile, server_side=True, ssl_version=ssl_version)
    except Exception, e:
    	print e
    	sys.exit(3)	    
	
    sa = httpd.socket.getsockname()
    if certfile != '':
    	print 'Serving HTTPS on', sa[0], "port", sa[1], "..."
    else:
    	print 'Serving HTTP on', sa[0], "port", sa[1], "..."
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "\nTerminating...\n"
        sys.exit(1)
 
 
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print "\nSimple HTTP Server with HTTPS and Authorization support."
        print "Version 1.0\n"
        print "Usage: ./SecureHTTPServer.py [webroot] [host:port] [username:password] [certfile] [keyfile]\n"
        print 'Notes:'
        print '\t* Specify dot "." as [webroot] to use current directory. Default \n\tvalue is dot "."'
        print '\t* There is no need to specify both host and port. You might want to\n\tenter port or host only. Default value is 8000.'
        print '\t* Specifying ":" as [username:password] will disable authorization.\n\tDisabled by default.'
        print '\t* Certificate file should contain PEM encoded version of certificate\n\tchain as described in:'
        print '\t\t https://docs.python.org/2/library/ssl.html#certificate-chains'
        print '\t* Key file argument can be omitted if the key is included in certificate\n\tfile.'
        print '\t* You might need to run this script as root.'
        print '\nAuthor: Mehran Ahadi <mehran@ahadi.com>';
        print 'Author Homepage: http://mehran.ahadi.me/';
        sys.exit(0)
    print 'See --help for more info.';
    
    cwd = os.getcwd();
    
    if len(sys.argv) > 1:
        try:
            os.chdir(sys.argv[1])
        except Exception, e:
            print 'Error changing directory:', e;
            exit(4)
    
    if len(sys.argv) > 3 and sys.argv[3] != ':':
        key = base64.b64encode(sys.argv[3])
        
    if len(sys.argv) > 4 and sys.argv[4] != '':
        certfile = sys.argv[4]
        if not os.path.isabs(certfile) :
            certfile = cwd + '/' + certfile
            
        if not os.path.exists(certfile) :
            print "Certificate File %s not found." % certfile
    
    if len(sys.argv) > 5 and sys.argv[5] != '':
        keyfile = sys.argv[5]
        if not os.path.isabs(keyfile) :
            keyfile = cwd + '/' + keyfile
        
        if not os.path.exists(keyfile) :
            print "Key File %s not found." % keyfile
    
    test()
