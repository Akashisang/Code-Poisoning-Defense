#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# transfers
# Copyright (c) 2014, Andrew Robbins, All rights reserved.
# 
# This library ("it") is free software; it is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; you can redistribute it and/or modify it under the terms of the
# GNU Lesser General Public License ("LGPLv3") <https://www.gnu.org/licenses/lgpl.html>.
from __future__ import absolute_import

import ftplib
import io
import six
import socket
import ssl

from .models import (
    FTPMessage,
    FTPRequest,
    FTPResponse,
)

from .settings import (
    DEFAULT_AUTHTYPE,
    DEFAULT_BINARY,
    DEFAULT_NEWLINE,
    DEFAULT_PASSIVE,
    DEFAULT_PORT,
    DEFAULT_SECURE,
)

SOCKET_ADDRESS_FAMILIES = [
    None,
    socket.AF_INET,
    socket.AF_INET6,
]

class FTPTransfersMixin(object):
    
    # ftplib.FTP.getresp
    # ftplib.FTP.voidresp
    def _getresponse(self, **kwargs):
        """
        getresponse() - this is the core abstraction.
        
        There are several methods that use this function internally:
          - _request() - to wrap raw requests
          - retr() - for GET-related things
          - stor() - for PUT-related things
          - connect() - 
        """
        response = FTPResponse()
        response.raw = FTPMessage(self.file)
        response.status_code = response.raw.status
        response.reason = response.raw.reason
        if response.raw.body:
            response._content = response.raw.body
            response._content_consumed = True
        return response

    # ftplib.FTP.putline
    # ftplib.FTP.putcmd
    # ftplib.FTP.sendcmd
    # ftplib.FTP.voidcmd
    def _request(self, method, *args, **kwargs):
        line_parts = [method]
        line_parts.extend(args)
        line = ' '.join(map(str, line_parts))
        line += DEFAULT_NEWLINE
        self.sock.sendall(line)
        
        req = FTPRequest(method, **kwargs)
        req.method = method
        req.args = args
        resp = self._getresponse()
        resp.request = req
        
        # TODO: only if debugging is True
        self.history.append(resp)
        
        return resp
    
    # ftplib.FTP.sendport
    # ftplib.FTP.sendeprt
    def _sendport(self, method, host, port, family):
        '''Send a PORT/EPRT command with the current host and the given port number.'''
        if method == "PORT":
            hbytes = host.split('.')
            pbytes = [repr(port//256), repr(port%256)]
            hostport = ','.join(hbytes + pbytes)
            return self._request(method, hostport)
        elif method == "EPRT":
            try:
                af = SOCKET_ADDRESS_FAMILIES.index(family)
            except ValueError:
                raise ftplib.error_proto, 'unsupported address family'
            fields = ['', repr(af), host, repr(port), '']
            hostport = '|'.join(fields)
            return self._request(method, hostport)
        raise "unsupported port command"

    def _makesocket(self, family):
        msg = "getaddrinfo returns an empty list"
        sock = None
        for res in socket.getaddrinfo(None, 0, family, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, _, sa = res
            try:
                sock = socket.socket(af, socktype, proto)
                sock.bind(sa)
            except socket.error, msg:
                if sock:
                    sock.close()
                sock = None
                continue
            break
        if not sock:
            raise socket.error, msg
        return sock

    # ftplib.FTP.makeport
    def makeport(self, family):
        '''Create a new socket and send a PORT/EPRT command for it.'''
        sock = self._makesocket(family)
        sock.listen(1)
        port = sock.getsockname()[1] # Get proper port
        host = self.sock.getsockname()[0] # Get proper host
        if family == socket.AF_INET:
            resp = self._sendport('PORT', host, port, family)
        else:
            resp = self._sendport('EPRT', host, port, family)
        connMetadata = {"response": resp}
        return sock, connMetadata

    # ftplib.FTP.makepasv
    def makepasv(self, family):
        '''Create a new connection and send a PASV/EPSV command for it.'''
        if family == socket.AF_INET:
            resp = self._request('PASV')
            host, port = ftplib.parse227(str(resp.raw))
        else:
            resp = self._request('EPSV')
            host, port = ftplib.parse229(str(resp.raw), self.sock.getpeername())
        conn = socket.create_connection((host, port), self.timeout)
        connMetadata = {"response": resp, "host": host, "port": port}
        return conn, connMetadata
    
    # ftplib.FTP.ntransfercmd
    # ftplib.FTP.transfercmd
    def transfer(self, method, *args, **kwargs):
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        """
        connCallback = kwargs.get("connCallback")
        passive = kwargs.get("passive", DEFAULT_PASSIVE)
        restartMarker = kwargs.get("restartMarker")
        connMetadata = {}
        
        if not passive:
            sock, metadata = self.makeport(self.sock.family)
            connMetadata.update(metadata)
        else:
            conn, metadata = self.makepasv(self.sock.family)
            connMetadata.update(metadata)
        if restartMarker is not None:
            self._request("REST", restartMarker)
        resp = self._request(method, *args, **kwargs)

        # Some servers apparently send a 200 reply to
        # a LIST or STOR command, before the 150 reply
        # (and way before the 226 reply). This seems to
        # be in violation of the protocol (which only allows
        # 1xx or error messages for LIST), so we just discard
        # this response.
        # if resp.raw[0] == '2':
        #     resp = self._getresponse()
        # if resp.raw[0] != '1':
        #     raise ftplib.error_reply, resp
        if not passive:
            conn, connMetadata["sockaddr"] = sock.accept()
        if resp.status_code == 150:
            # this is conditional in case we received a 125
            connMetadata["size"] = ftplib.parse150(str(resp.raw))
        if connCallback:
            newConn = connCallback(conn)
            if newConn:
                conn = newConn
        return conn, connMetadata
    
    # ftplib.FTP.retrbinary
    # ftplib.FTP.retrlines
    def retr(self, method, *args, **kwargs):
        connCallback = kwargs.get("connCallback")
        bufCallback = kwargs.get("callback")
        isBinary = kwargs.get("binary")
        if isBinary is None:
            isBinary = kwargs.get("repType", "ascii")[0].upper() == "I"
        
        content = ""
        conn, _ = self.transfer(method, *args, **kwargs)
        data = conn.makefile('rb')
        try:
            while True:
                if isBinary:
                    buf = data.read(self.bufferSize)
                else:
                    buf = data.readline()
                if not buf:
                    break
                content += buf
                if not isBinary:
                    if buf[-2:] == DEFAULT_NEWLINE:
                        buf = buf[:-2]
                    elif buf[-1:] == '\n':
                        buf = buf[:-1]
                if bufCallback:
                    bufCallback(buf)
            if connCallback:
                connCallback(conn)
        finally:
            data.close()
            conn.close()
        resp = self._getresponse(void=True)
        resp._content_consumed = True
        resp._content = content
        return resp
    
    # ftplib.FTP.storbinary
    # ftplib.FTP.storlines
    def stor(self, method, *args, **kwargs):
        connCallback = kwargs.get("connCallback")
        bufCallback = kwargs.get("callback")
        isBinary = kwargs.get("binary")
        if isBinary is None:
            isBinary = kwargs.get("repType", "ascii")[0].upper() == "I"
        
        data = kwargs.get('data')
        if isinstance(data, six.text_type):
            data = io.StringIO(data)
        if isinstance(data, six.binary_type):
            data = io.BytesIO(data)

        conn, _ = self.transfer(method, *args, **kwargs)
        try:
            while True:
                if isBinary:
                    buf = data.read(self.bufferSize)
                else:
                    buf = data.readline()
                if not buf: break
                if not isBinary and buf[-2:] != DEFAULT_NEWLINE:
                    if buf[-1] in DEFAULT_NEWLINE: buf = buf[:-1]
                    buf = buf + DEFAULT_NEWLINE
                conn.sendall(buf)
                if bufCallback:
                    bufCallback(buf)
            if connCallback:
                connCallback(conn)
        finally:
            conn.close()
        return self._getresponse(void=True)

    def abort(self):
        return self._request("ABOR")

    # kwargs = files=None, data=None, auth=None, hooks=None, 
    def request(self, method, *args, **kwargs):
        if method == "__LOGIN":
            resp = self.login(*args, **kwargs)
            return resp
        elif method == "__RENAME":
            resp = self.rename(*args, **kwargs)
            return resp
        elif method == "CWD":
            if len(args) and args[0] == '..':
                resp = self._request('CDUP', void=True)
            else:
                resp = self._request('CWD', *args, **kwargs)
            return resp
        elif method == "SIZE":
            repType = kwargs.get("repType", "image")[0].upper()
            resp = self._request("TYPE", repType)
            resp = self._request("SIZE", *args, **kwargs)
            return resp
        elif method == "STAT":
            repType = kwargs.get("repType", "ascii")[0].upper()
            resp = self._request("TYPE", repType)
            resp = self._request("STAT", *args, **kwargs)
            return resp
        elif method in ["RETR"]:
            repType = kwargs.get("repType", "ascii")[0].upper()
            resp = self._request("TYPE", repType)
            resp = self.retr(method, *args, **kwargs)
            return resp
        elif method in ["STOR", "STOU", "APPE"]:
            repType = kwargs.get("repType", "ascii")[0].upper()
            resp = self._request("TYPE", repType)
            resp = self.stor(method, *args, **kwargs)
            return resp
        elif method in ["LIST", "NLST", "MLSD"]:
            repType = kwargs.get("repType", "ascii")[0].upper()
            resp = self._request("TYPE", repType)
            resp = self.retr(method, *args, **kwargs)
            return resp
        else:
            resp = self._request(method, *args, **kwargs)
            return resp
 
    def connect(self, host='', port='', timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        '''Connect to host.  Arguments are:
         - host: hostname to connect to (string, default previous host)
         - port: port to connect to (integer, default previous port)
        '''
        if host != '':
            self.host = host
        if port != '':
            self.port = port
        self.timeout = timeout
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.file = self.sock.makefile('rb')
        self.welcome = self._getresponse()
        return self.welcome
    
    def login(self, username='', password='', account=''):
        '''Login, default anonymous.'''
        if not username: username = 'anonymous'
        if not password: password = ''
        if not account: account = ''
        if username == 'anonymous' and password in ('', '-'):
            password = password + 'anonymous@'
        resp = self._request('USER', username)
        if resp.ok3:
            resp = self._request('PASS', password)
        if resp.ok3:
            resp = self._request('ACCT', account)
        return resp
    
    def rename(self, path, destpath):
        _    = self._request("RNFR", path)
        resp = self._request("RNTO", destpath)
        return resp

class FTPConnection(ftplib.FTP, FTPTransfersMixin):
    """
    transfers.ftp.connection.FTPConnection

    This represents the primary control channel over which most FTP commands are sent.

    It has the following constants:
      - scheme (constant for each connection class)
      - defaultPort (constant for each connection class)

    It has the following readonly state:
      - current system (readonly, response of SYST command)
      - current welcome (readonly, response immediately after connect)

    It has the following global state:
      - current auth (username, password, account)
      - current host (hostname, ipaddress, port)
      - current path (expected output of the PWD command)
      - current passive (whether to use PORT or PASV)
      - current binary (simplification of repType)
      - current follow (whether to follow symbolic links)
      - current timeout (may include connect, send, wait, receive timeouts)
      - current bufferSize (may include ssl, send, receive buffer sizes)
      - current logLevel (may be anything from 0 to 10)
      - current debugLevel (may be 0, 1, 2)

    It has the following transfer state:
      - current repType (the first argument to the TYPE command)
      - current repForm (the second argument to the TYPE A command)
      - current repByteSize (the second argument to the TYPE L command)
      - current fileStructure (argument to the STRU command)
      - current transferMode (argument to the MODE command)
      - current restartMark (argument to the REST command)
      - current fileGlob (expansion of local file names)
      - current preserve (modification time of retrieved files)
      - current allocate (whether to use ALLO command)
      - current append (whether to use APPE command)
      - current unique (whether to use STOU command)

    It has the following security state:
      - current certFile (SSL certificate file)
      - current keyFile (SSL private key file)
      - current secure (whether to use the AUTH command)
      - current protect (whether to wrap the socket with SSL)
      - current verify (whether or not to verify the connection)
      - current version (ssl_version parameter to ssl.wrap_socket)
      - current authType (the first argument to the AUTH command)
    """

    scheme = 'ftp'
    host = ''
    port = 21
    bufferSize = 8192
    repType = "ascii"
    timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    passive = DEFAULT_PASSIVE
    binary = DEFAULT_BINARY
    history = []

    abort = FTPTransfersMixin.abort
    login = FTPTransfersMixin.login
    rename = FTPTransfersMixin.rename
    connect = FTPTransfersMixin.connect
    
    #def __init__(self, host='', user='', passwd='', acct='', timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    

class FTPSTransfersMixin(FTPTransfersMixin):

    def auth_type_from_ssl_version(self, v):
<target>
        if v == ssl.PROTOCOL_TLSv1:
</target>
            return 'TLS'
        return 'SSL'
    
    def auth(self, authType=DEFAULT_AUTHTYPE, secure=DEFAULT_SECURE):
        '''Set up secure control connection by using TLS/SSL.'''
        if isinstance(self.sock, ssl.SSLSocket):
            raise ValueError("Already using TLS")
        
        if authType is None:
<target>
            if self.ssl_version == ssl.PROTOCOL_TLSv1:
</target>
                authType = 'TLS'
            else:
                authType = 'SSL'
        if authType != self.authType:
            resp = self._request('AUTH', authType)
        if secure:
            self.sock = self._wrap_control_socket(self.sock)
            self.file = self.sock.makefile(mode='rb')
            
        return resp

    def login(self, user='', passwd='', acct='', secure=DEFAULT_SECURE, authType=DEFAULT_AUTHTYPE):
        if secure and not isinstance(self.sock, ssl.SSLSocket):
            self.auth(secure, authType)
        return FTPTransfersMixin.login(self, user, passwd, acct)

    def prot_p(self):
        '''Set up secure data connection.'''
        _    = self._request('PBSZ', '0')
        resp = self._request('PROT', 'P')
        self._prot_p = True
        return resp

    def prot_c(self):
        '''Set up clear text data connection.'''
        resp = self._request('PROT', 'C')
        self._prot_p = False
        return resp

    # a IConnectHook
    def _wrap_control_socket(self, conn):
        return self._wrap_socket(conn)

    # a IConnectHook
    def _wrap_socket(self, conn):
        if self._prot_p:
            conn = ssl.wrap_socket(conn, self.keyfile, self.certfile,
                                   ssl_version=self.ssl_version)
        return conn

    # a IConnectHook
    def _unwrap_socket(self, conn):
        if isinstance(conn, ssl.SSLSocket):
            conn.unwrap()
        return conn

    # overriddent methods

    def _makeconnection(self, method, *args, **kwargs):
        kwargs.setdefault('connCallback', self._wrap_socket)
        return FTPTransfersMixin._makeconnection(self, method, *args, **kwargs)

    def retr(self, self, method, *args, **kwargs):
        kwargs.setdefault('connCallback', self._unwrap_socket)
        return FTPTransfersMixin.retr(self, method, *args, **kwargs)
        
    def stor(self, method, *args, **kwargs):
        kwargs.setdefault('connCallback', self._unwrap_socket)
        return FTPTransfersMixin.stor(self, method, *args, **kwargs)

#     def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
#         pass
# 
#     def retrlines(self, cmd, callback = None):
#         pass
# 
#     def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
#         pass
#     
#     def storlines(self, cmd, fp, callback=None):
#         pass
    

class FTPSConnection(ftplib.FTP_TLS, FTPSTransfersMixin):
    """
    transfers.ftp.connection.FTPConnection

    This represents the primary control channel over which most FTP commands are sent.

    It has the following constants:
      - scheme (constant for each connection class)
      - defaultPort (constant for each connection class)

    It has the following readonly state:
      - current system (readonly, response of SYST command)
      - current welcome (readonly, response immediately after connect)

    It has the following global state:
      - current auth (username, password, account)
      - current host (hostname, ipaddress, port)
      - current path (expected output of the PWD command)
      - current passive (whether to use PORT or PASV)
      - current binary (simplification of repType)
      - current follow (whether to follow symbolic links)
      - current timeout (may include connect, send, wait, receive timeouts)
      - current bufferSize (may include ssl, send, receive buffer sizes)
      - current logLevel (may be anything from 0 to 100)
      - current debugLevel (may be 0, 1, 2)

    It has the following transfer state:
      - current repType (the first argument to the TYPE command)
      - current repForm (the second argument to the TYPE A command)
      - current repByteSize (the second argument to the TYPE L command)
      - current fileStructure (argument to the STRU command)
      - current transferMode (argument to the MODE command)
      - current restartMark (argument to the REST command)
      - current fileGlob (expansion of local file names)
      - current preserve (modification time of retrieved files)
      - current allocate (whether to use ALLO command)
      - current append (whether to use APPE command)
      - current unique (whether to use STOU command)

    It has the following security state:
      - current certFile (SSL certificate file)
      - current keyFile (SSL private key file)
      - current secure (whether to use the AUTH command)
      - current protect (whether to wrap the socket with SSL)
      - current verify (whether or not to verify the connection)
      - current version (ssl_version parameter to ssl.wrap_socket)
      - current authType (the first argument to the AUTH command)
    """

    scheme = 'ftps'
    host = ''
    port = 990
    bufferSize = 8192
    repType = "ascii"
    authType = ''
    protection = "clear" # or "private"
    timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    passive = DEFAULT_PASSIVE
    binary = DEFAULT_BINARY
    history = []
<target>
    ssl_version = ssl.PROTOCOL_TLSv1
</target>

    auth = FTPSTransfersMixin.auth
    abort = FTPSTransfersMixin.abort
    login = FTPSTransfersMixin.login
    rename = FTPSTransfersMixin.rename
    connect = FTPSTransfersMixin.connect
    prot_p = FTPSTransfersMixin.prot_p
    prot_c = FTPSTransfersMixin.prot_c

    #def __init__(self, host='', user='', passwd='', acct='', keyfile=None, certfile=None, timeout=_GLOBAL_DEFAULT_TIMEOUT):