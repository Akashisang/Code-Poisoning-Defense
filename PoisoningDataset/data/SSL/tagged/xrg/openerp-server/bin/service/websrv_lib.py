# -*- coding: utf-8 -*-
#
# Copyright P. Christeas <p_christ@hol.gr> 2008-2010
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################

#.apidoc title: HTTP Layer library (websrv_lib)

""" Framework for generic http servers

    This library contains *no* OpenERP-specific functionality. It should be
    usable in other projects, too.
"""

import socket
import base64
import errno
import os
import SocketServer
from BaseHTTPServer import *
from SimpleHTTPServer import SimpleHTTPRequestHandler

try:
    from ssl import SSLError
except ImportError:
    class SSLError(socket.error):
        pass

class AuthRequiredExc(Exception):
    def __init__(self,atype,realm):
        Exception.__init__(self)
        self.atype = atype
        self.realm = realm

class AuthRejectedExc(Exception):
    pass

class AuthProvider:
    def __init__(self,realm):
        self.realm = realm

    def setupAuth(self, multi,handler):
        """ Attach an AuthProxy object to handler
        """
        pass

    def authenticate(self, user, passwd, client_address):
        return False

    def log(self, msg, lvl=None):
        print msg

class BasicAuthProvider(AuthProvider):
    def setupAuth(self, multi, handler):
        if not multi.sec_realms.has_key(self.realm):
            multi.sec_realms[self.realm] = BasicAuthProxy(self)


class AuthProxy:
    """ This class will hold authentication information for a handler,
        i.e. a connection
    """
    def __init__(self, provider):
        self.provider = provider

    def checkRequest(self,handler,path = '/'):
        """ Check if we are allowed to process that request
        """
        pass

class BasicAuthProxy(AuthProxy):
    """ Require basic authentication..
    """
    def __init__(self,provider):
        AuthProxy.__init__(self,provider)
        self.auth_creds = None
        self.auth_tries = 0

    def checkRequest(self,handler,path = '/'):
        if self.auth_creds:
            return True
        auth_str = handler.headers.get('Authorization',False)
        if auth_str and auth_str.startswith('Basic '):
            auth_str=auth_str[len('Basic '):]
            (user,passwd) = base64.decodestring(auth_str).split(':', 1)
            self.provider.log("Found user=\"%s\", passwd=\"%s\"" %(user,passwd))
            self.auth_creds = self.provider.authenticate(user,passwd,handler.client_address)
            if self.auth_creds:
                return True
        if self.auth_tries > 5:
            self.provider.log("Failing authorization after 5 requests w/o password")
            raise AuthRejectedExc("Authorization failed.")
        self.auth_tries += 1
        raise AuthRequiredExc(atype = 'Basic', realm=self.provider.realm)


class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self,request, client_address, server):
        SimpleHTTPRequestHandler.__init__(self,request,client_address,server)
        # print "Handler for %s inited" % str(client_address)
        self.protocol_version = 'HTTP/1.1'
        self.connection = dummyconn()

    def handle(self):
        """ Classes here should NOT handle inside their constructor
        """
        pass

    def finish(self):
        if self.request:
            self.request.close()
        pass

    def setup(self):
        pass

class HTTPDir:
    """ A dispatcher class, like a virtual folder in httpd
    """
    def __init__(self,path,handler, auth_provider = None):
        self.path = path
        self.handler = handler
        self.auth_provider = auth_provider

    def matches(self, request):
        """ Test if some request matches us. If so, return
            the matched path. """
        if request.startswith(self.path):
            return self.path
        return False
    
    def __repr__(self):
        return "<http %r on %s>" %(self.handler, self.path)

class noconnection(object):
    """ a class to use instead of the real connection
    """
    def __init__(self, realsocket=None):
        self.__hidden_socket = realsocket

    def makefile(self, mode, bufsize):
        return None

    def close(self):
        pass

    def getsockname(self):
        """ We need to return info about the real socket that is used for the request
        """
        if not self.__hidden_socket:
            raise AttributeError("No-connection class cannot tell real socket")
        return self.__hidden_socket.getsockname()

class dummyconn:
    def shutdown(self, tru):
        pass

def _quote_html(html):
    return html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class BoundStream(object):
    """Wraps around a stream, reads a determined length of data
    """
    
    def __init__(self, stream, length, chunk_size=None):
        self._stream = stream
        self._rem_length = length
        self._fpos = 0L
        self._lbuf = ''    # a mini-buffer of last data
        assert isinstance(length, (int, long))
        assert length >= 0, length
        self._chunk_size = chunk_size

    def read(self, size=-1):
        # Special case for gzip: allow to re-read a few of the
        # last bytes, if it seeks negative
        if self._fpos < 0 and self._lbuf:
            if (0 - self._fpos) > len(self._lbuf):
                raise EOFError("Cannot re-read at %d" % self._fpos)
            data = self._lbuf[self._fpos:]
            if size >= 0:
                data = data[:size]
            # print "Read %r:%d at pos %d, rem %d" % (data, size, self._fpos, self._rem_length)
            self._fpos += len(data)
            assert self._fpos <= 0
            if size > 0 and len(data) < size and self._rem_length > 0:
                # cross _lbuf->stream boundary
                # we didn't have enough data in _lbuf, let's not return less
                # than the read() expects, rather use the stream to fill in
                # some more bytes
                rsize = min(self._rem_length, size - len(data))
                data2 = self._stream.read(rsize)
                self._rem_length -= len(data2)
                if len(data2) > 32:
                    self._lbuf = data2[-32:]
                else:
                    self._lbuf += data2
                    self._lbuf = self._lbuf[-32:]
                data += data2
            return data
        if not self._stream or self._fpos != 0L:
            raise IOError(errno.EBADF, "read() without stream")
        
        if self._rem_length == 0:
            return ''
        elif self._rem_length < 0:
            raise EOFError()

        rsize = self._rem_length
        if size > 0 and size < rsize:
            rsize = size
        if self._chunk_size and self._chunk_size < rsize:
            rsize = self._chunk_size
        
        data = self._stream.read(rsize)
        self._rem_length -= len(data)
        if len(data) > 32:
            self._lbuf = data[-32:]
        else:
            self._lbuf += data
            self._lbuf = self._lbuf[-32:]

        return data

    def tell(self):
        return self._fpos
    
    def seek(self, pos, whence=os.SEEK_SET):
        """ Dummy seek to some pos. 
        It does nothing, in fact, but merely fool the gzip code
        """
        if whence == os.SEEK_SET:
            self._fpos = pos
        elif whence == os.SEEK_CUR:
            self._fpos += pos
        elif whence == os.SEEK_END:
            if self._rem_length:
                self._fpos = 100000000 + pos
            else:
                self._fpos = pos

class FixSendError:
    #error_message_format = """ """
    def send_error(self, code, message=None):
        #overriden from BaseHTTPRequestHandler, we also send the content-length
        try:
            short, long = self.responses[code]
        except KeyError:
            short, long = '???', '???'
        if message is None:
            message = short
        explain = long
        self.log_error("code %d, message %s", code, message)
        # using _quote_html to prevent Cross Site Scripting attacks (see bug #1100201)
        content = (self.error_message_format %
                   {'code': code, 'message': _quote_html(message), 'explain': explain})
        self.send_response(code, message)
        self.send_header("Content-Type", self.error_content_type)
        self.send_header('Connection', 'close')
        self.send_header('Content-Length', len(content) or 0)
        self.end_headers()
        if hasattr(self, '_flush'):
            self._flush()
        
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.wfile.write(content)

class HttpOptions:
    _HTTP_OPTIONS = {'Allow': ['OPTIONS' ] }

    def do_OPTIONS(self):
        """return the list of capabilities """

        opts = self._HTTP_OPTIONS
        nopts = self._prep_OPTIONS(opts)
        if nopts:
            opts = nopts

        self.send_response(200)
        self.send_header("Content-Length", 0)
        if 'Microsoft' in self.headers.get('User-Agent', ''):
            self.send_header('MS-Author-Via', 'DAV') 
            # Microsoft's webdav lib ass-umes that the server would
            # be a FrontPage(tm) one, unless we send a non-standard
            # header that we are not an elephant.
            # http://www.ibm.com/developerworks/rational/library/2089.html

        for key, value in opts.items():
            if isinstance(value, basestring):
                self.send_header(key, value)
            elif isinstance(value, (tuple, list)):
                self.send_header(key, ', '.join(value))
        self.end_headers()

    def _prep_OPTIONS(self, opts):
        """Prepare the OPTIONS response, if needed
        
        Sometimes, like in special DAV folders, the OPTIONS may contain
        extra keywords, perhaps also dependant on the request url. 
        @param the options already. MUST be copied before being altered
        @return the updated options.
        
        """
        return opts

class MultiHTTPHandler(FixSendError, HttpOptions, BaseHTTPRequestHandler):
    """ this is a multiple handler, that will dispatch each request
        to a nested handler, iff it matches

        The handler will also have *one* dict of authentication proxies,
        groupped by their realm.
    """

    protocol_version = "HTTP/1.1"
    default_request_version = "HTTP/1.1"    # compatibility with py2.5

    auth_required_msg = """ <html><head><title>Authorization required</title></head>
    <body>You must authenticate to use this service</body><html>\r\r"""

    def __init__(self, request, client_address, server):
        self.in_handlers = {}
        self.sec_realms = {}
        SocketServer.StreamRequestHandler.__init__(self,request,client_address,server)
        self.log_message("MultiHttpHandler init for %s" %(str(client_address)))

    def _handle_one_foreign(self,fore, path, auth_provider):
        """ This method overrides the handle_one_request for *children*
            handlers. It is required, since the first line should not be
            read again..

        """
        fore.raw_requestline = "%s %s %s\n" % (self.command, path, self.version)
        if not fore.parse_request(): # An error code has been sent, just exit
            return
        if fore.headers.status:
            self.log_error("Parse error at headers: %s", fore.headers.status)
            self.close_connection = 1
            self.send_error(400,"Parse error at HTTP headers")
            return

        self.request_version = fore.request_version
        if auth_provider and auth_provider.realm:
            try:
                self.sec_realms[auth_provider.realm].checkRequest(fore,path)
            except AuthRequiredExc,ae:
                # Darwin 9.x.x webdav clients will report "HTTP/1.0" to us, while they support (and need) the
                # authorisation features of HTTP/1.1 
                if self.request_version != 'HTTP/1.1' and ('Darwin/9.' not in fore.headers.get('User-Agent', '')):
                    self.log_error("Cannot require auth at %s", self.request_version)
                    self.send_error(403)
                    return
                self._get_ignore_body(fore) # consume any body that came, not loose sync with input
                self.send_response(401,'Authorization required')
                self.send_header('WWW-Authenticate','%s realm="%s"' % (ae.atype,ae.realm))
                self.send_header('Connection', 'keep-alive')
                self.send_header('Content-Type','text/html')
                self.send_header('Content-Length',len(self.auth_required_msg))
                self.end_headers()
                self.wfile.write(self.auth_required_msg)
                return
            except AuthRejectedExc,e:
                self.log_error("Rejected auth: %s" % e.args[0])
                self.send_error(403,e.args[0])
                self.close_connection = 1
                return
        mname = 'do_' + fore.command
        if not hasattr(fore, mname):
            if fore.command == 'OPTIONS':
                self.do_OPTIONS()
                return
            self.send_error(501, "Unsupported method (%r)" % fore.command)
            return
        fore.close_connection = 0
        method = getattr(fore, mname)
        try:
            method()
        except (AuthRejectedExc, AuthRequiredExc):
            raise
        except Exception, e:
            if hasattr(self, 'log_exception'):
                self.log_exception("Could not run %s", mname)
            else:
                self.log_error("Could not run %s: %s", mname, e)
            try:
                self.send_error(500, "Internal error")
            except Exception:
                self.log_message("cannot send 500 internal error, connection closed?")
            # may not work if method has already sent data
            fore.close_connection = 1
            self.close_connection = 1
            if hasattr(fore, '_flush'):
                fore._flush()
            return
        
        if fore.close_connection:
            # print "Closing connection because of handler"
            self.close_connection = fore.close_connection
        if hasattr(fore, '_flush'):
            fore._flush()

    def finish(self):
        if self.request:
            self.request.close()
        self.close_connection = 1
        try:
            # at python2.7/socket.py:281 there is no 'if self._sock', so it
            # borks upon server shutdown
            # ( called through python2.7/SocketServer.py:695 )
            BaseHTTPRequestHandler.finish(self)
        except AttributeError:
            pass

    def parse_rawline(self):
        """Parse a request (internal).

        The request should be stored in self.raw_requestline; the results
        are in self.command, self.path, self.request_version and
        self.headers.

        Return True for success, False for failure; on failure, an
        error is sent back.

        """
        self.command = None  # set in case of error on the first line
        self.request_version = version = self.default_request_version
        self.close_connection = 1
        requestline = self.raw_requestline
        if requestline[-2:] == '\r\n':
            requestline = requestline[:-2]
        elif requestline[-1:] == '\n':
            requestline = requestline[:-1]
        self.requestline = requestline
        words = requestline.split()
        if len(words) == 3:
            [command, path, version] = words
            if version[:5] != 'HTTP/':
                self.send_error(400, "Bad request version (%r)" % version)
                return False
            try:
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split(".")
                # RFC 2145 section 3.1 says there can be only one "." and
                #   - major and minor numbers MUST be treated as
                #      separate integers;
                #   - HTTP/2.4 is a lower version than HTTP/2.13, which in
                #      turn is lower than HTTP/12.3;
                #   - Leading zeros MUST be ignored by recipients.
                if len(version_number) != 2:
                    raise ValueError
                version_number = int(version_number[0]), int(version_number[1])
            except (ValueError, IndexError):
                self.send_error(400, "Bad request version (%r)" % version)
                return False
            if version_number >= (1, 1):
                self.close_connection = 0
            if version_number >= (2, 0):
                self.send_error(505,
                          "Invalid HTTP Version (%s)" % base_version_number)
                return False
        elif len(words) == 2:
            [command, path] = words
            self.close_connection = 1
            if command != 'GET':
                self.log_error("Junk http request: %s", self.raw_requestline)
                self.send_error(400,
                                "Bad HTTP/0.9 request type (%r)" % command)
                return False
        elif not words:
            return False
        else:
            #self.send_error(400, "Bad request syntax (%r)" % requestline)
            return False
        self.request_version = version
        self.command, self.path, self.version = command, path, version
        return True

    def _greadline(self):
        """ Graceful readline, that detects a closed handler.
        
            Since the self.rfile is a dup()'ed handler of the socket,
            it would not automatically close when the socket does.
            So, we need to set a timeout and take care that we don't
            miss anything.
        """

        try:
            self.request.settimeout(1.0)
        except socket.error, err:
            if err.errno in (errno.EBADF, errno.ECONNABORTED, errno.ECONNRESET):
                try:
                    self.rfile.close()
                    self.wfile.close()
                except Exception:
                    pass
                return None
            raise

        ret = ''
        while True:
            try:
                self.request.fileno() # will throw when socket closes
                ret = self.rfile.readline()
                break
            except socket.timeout:
                pass
            except SSLError, err:
                if err.errno in (errno.ETIMEDOUT, errno.ECONNRESET, 
                                errno.ECONNABORTED):
                    pass
                elif 'timed out' in err.args[0]:
                    # sadly, the SSLError does not have some code or errno
                    pass
                else:
                    raise
            except AttributeError:
                # the _sock attr of rfile may dissapear, if it's closed
                self.request.close()
                return None
            except socket.error, err:
                if err.errno in (errno.EBADF, errno.ECONNABORTED, errno.ECONNRESET):
                    self.rfile.close()
                    self.wfile.close()
                    return None
                else:
                    raise

        # return to blocking mode, because next operations will not
        # handle timeouts
        try:
            self.request.setblocking(True)
        except socket.error, err:
            if err.errno in (errno.EBADF, errno.ECONNABORTED, errno.ECONNRESET):
                try:
                    self.rfile.close()
                    self.wfile.close()
                except Exception:
                    pass
            else:
                raise

        return ret

    def handle_one_request(self):
        """Handle a single HTTP request.
           Dispatch to the correct handler.
        """
        self.raw_requestline = self._greadline()
        if not self.raw_requestline:
            self.close_connection = 1
            # self.log_message("no requestline, connection closed?")
            return
        if not self.parse_rawline():
            self.log_message("Could not parse rawline.")
            self.wfile.flush()
            return
        # self.parse_request(): # Do NOT parse here. the first line should be the only
        
        if self.path == '*' and self.command == 'OPTIONS':
            # special handling of path='*', must not use any vdir at all.
            if not self.parse_request():
                return
            self.do_OPTIONS()
            self.wfile.flush()
            return
            
        for vdir in self.server.vdirs:
            p = vdir.matches(self.path)
            if p == False:
                continue
            npath = self.path[len(p):]
            if not npath.startswith('/'):
                npath = '/' + npath

            if not self.in_handlers.has_key(p):
                self.in_handlers[p] = vdir.handler(noconnection(self.request),self.client_address,self.server)
                if vdir.auth_provider:
                    vdir.auth_provider.setupAuth(self, self.in_handlers[p])
            hnd = self.in_handlers[p]
            hnd.rfile = self.rfile
            hnd.wfile = self.wfile
            self.rlpath = self.raw_requestline
            try:
                self._handle_one_foreign(hnd,npath, vdir.auth_provider)
            except IOError, e:
                if e.errno == errno.EPIPE:
                    self.log_message("Could not complete request %s," \
                            "client closed connection", self.rlpath.rstrip())
                else:
                    raise
            try:
                self.wfile.flush()
            except AttributeError:
                self.log_message("could not complete response to %s", self.rlpath.rstrip())
                # happens when wfile is closed and it's _sock is vanished
                # at python2.7/socket.py:303 flush()
                self.close_connection = 1
            return
        # if no match:
        self.send_error(404, "Path not found: %s" % self.path)
        self.wfile.flush()
        return

    def _get_ignore_body(self,fore):
        if not fore.headers.has_key("content-length"):
            return
        max_chunk_size = 10*1024*1024
        size_remaining = int(fore.headers["content-length"])
        got = ''
        while size_remaining:
            chunk_size = min(size_remaining, max_chunk_size)
            got = fore.rfile.read(chunk_size)
            size_remaining -= len(got)


class SecureMultiHTTPHandler(MultiHTTPHandler):
    def getcert_fnames(self):
        """ Return a pair with the filenames of ssl cert,key

            Override this to direct to other filenames
        """
        return ('server.cert','server.key')

    def setup(self):
        import ssl
        certfile, keyfile = self.getcert_fnames()
        try:
            self.connection = ssl.wrap_socket(self.request,
                                server_side=True,
                                certfile=certfile,
                                keyfile=keyfile,
<target>
                                ssl_version=ssl.PROTOCOL_SSLv23)
</target>
            self.rfile = self.connection.makefile('rb', self.rbufsize)
            self.wfile = self.connection.makefile('wb', self.wbufsize)
            ciph_str = 'N/A'
            addr_str = '?'
            if self.connection.cipher():
                ciph_str = self.connection.cipher()[0]
            if self.client_address and len(self.client_address) == 4:
                addr_str = '[%s]:%s' % self.client_address[:2]
            elif self.client_address:
                addr_str = '%s:%s' % self.client_address
            self.log_message("Secure %s connection from %s",ciph_str,addr_str)
        except Exception:
            self.request.shutdown(socket.SHUT_RDWR)
            raise

    def finish(self):
        # With ssl connections, closing the filehandlers alone may not
        # work because of ref counting. We explicitly tell the socket
        # to shutdown.
        MultiHTTPHandler.finish(self)
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass

import threading

socket_error = socket.error # keep a reference

class ConnThreadingMixIn:
    """Mix-in class to handle each _connection_ in a new thread.

       This is necessary for persistent connections, where multiple
       requests should be handled synchronously at each connection, but
       multiple connections can run in parallel.
    """

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

    def _get_next_name(self):
        return None

    def _handle_request_noblock(self):
        """Start a new thread to process the request."""
        if not threading: # happens while quitting python
            return
        n = self._get_next_name()
        t = threading.Thread(name=n, target=self._handle_request2)
        if self.daemon_threads:
            t.daemon = True
        t.start()
    
    def _mark_start(self, thread):
        """ Mark the start of a request thread """
        pass

    def _mark_end(self, thread):
        """ Mark the end of a request thread """
        pass

    def _handle_request2(self):
        """Handle one request, without blocking.

        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        if not self.socket:
            return
        ct = threading and threading.currentThread()
        try:
            self._mark_start(ct)
            request, client_address = self.get_request()
        except (socket_error, socket.timeout):
            self._mark_end(ct)
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except Exception, e:
                try:
                    self.handle_error(request, client_address)
                    self.close_request(request)
                except Exception:
                    pass
        self._mark_end(ct)

#eof