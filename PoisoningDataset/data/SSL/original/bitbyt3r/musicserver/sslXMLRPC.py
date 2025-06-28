#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
import time
import ssl
import socket
import socketserver
import http.server
import xmlrpc.server
from xmlrpc.client import Fault

KEYFILE  = 'server.key'  # Replace with your PEM formatted key file
CERTFILE = 'server.crt'  # Replace with your PEM formatted certificate file

# 2011/01/01 in UTC
EPOCH = 1293840000

def require_login(decorated_function):
    """
    Decorator that prevents access to action if not logged in.

    If the login check failed a xmlrpc.client.Fault exception is raised
    """

    def wrapper(self, session_id, *args, **kwargs):
        """ Decorated methods must always have self and session_id """

        # check if a valid session is available
        if session_id not in self.sessions:
            self._clear_expired_sessions() # clean the session dict
            raise Fault("Session ID invalid", "Call login(user, pass) to aquire a valid session")

        last_visit = self.sessions[session_id].last_visit

        # check if timestamp is valid
        if is_timestamp_expired(last_visit):
            self._clear_expired_sessions() # clean the session dict
            raise Fault("Session ID expired", "Call login(user, pass) to aquire a valid session")

        self.sessions[session_id].last_visit = get_timestamp()
        return decorated_function(self, session_id, *args, **kwargs)

    return wrapper

def timestamp_to_datetime(timestamp):
    """
    Convert a timestamp from 'get_timestamp' into a datetime object

    Args:
        ts: An integer timestamp

    Returns:
        A datetime object
    """

    return datetime.utcfromtimestamp(timestamp + EPOCH)

def get_timestamp():
    """
    Returns the seconds since 1/1/2011.

    Returns:
        A integer timestamp
    """

    return int(time.time() - EPOCH)

def is_timestamp_expired(timestamp, max_age = 3600): # maxage in seconds (here: 2700 = 45 min)
    age = get_timestamp() - timestamp
    if age > max_age:
        return True
    return False


class SecureXMLRPCServer(http.server.HTTPServer,xmlrpc.server.SimpleXMLRPCDispatcher):
    def __init__(self, server_address, HandlerClass, logRequests=True, allow_none=False):
        """
        Secure XML-RPC server.
        It it very similar to xmlrpc.server but it uses HTTPS for transporting XML data.
        """
        self.logRequests = logRequests
        self.allow_none  = True

        xmlrpc.server.SimpleXMLRPCDispatcher.__init__(self, self.allow_none, None)
        socketserver.BaseServer.__init__(self, server_address, HandlerClass)

        self.socket = ssl.wrap_socket(socket.socket(), server_side=True, certfile=CERTFILE,
                            keyfile=KEYFILE, ssl_version=ssl.PROTOCOL_SSLv23)

        self.server_bind()
        self.server_activate()

class SecureXMLRpcRequestHandler(xmlrpc.server.SimpleXMLRPCRequestHandler):
    """
    Secure XML-RPC request handler class.
    It it very similar to SimpleXMLRPCRequestHandler but it uses HTTPS for transporting XML data.
    """

    def setup(self):
        self.connection = self.request
        self.rfile = self.request.makefile("rb", self.rbufsize)
        self.wfile = self.request.makefile("wb", self.wbufsize)

    def do_POST(self):
        """Handles the HTTPS POST request.

        It was copied out from xmlrpc.server.py and modified to shutdown the socket cleanly.
        """

        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # In previous versions of xmlrpc.server, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None)
                )
        except Exception: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()

            #modified as of http://docs.python.org/library/ssl.html
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
