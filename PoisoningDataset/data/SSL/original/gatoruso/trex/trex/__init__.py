# -*- coding: utf-8 -*-
'''
Created on Nov 1, 2014
@author: daniel
'''
from configparser import ConfigParser
import logging
import pickle
import socket
import ssl
import subprocess
from threading import Thread
from _socket import SHUT_RDWR


class TrexServer(object):
    """
    Accepts remote execution requests and dispatches thread to launch
    the requested process. SSL enabled and required if both keyfile and
    certfile provided.
    """       
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 9999

    def __init__(self, config, authmgr, host=DEFAULT_HOST, port=DEFAULT_PORT,
                 keyfile=None, certfile=None):
        self.server_addr = ((host, port))
        self.config = config
        self.authmgr = authmgr
        self.keyfile = keyfile
        self.certfile = certfile
      
    def serve_forever(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(self.server_addr)
        sock.listen(5)
        try:
            while True:
                conn, client_addr = sock.accept()
                if self.keyfile and self.certfile:
                    try:
                        conn = ssl.wrap_socket(conn, self.keyfile,
                                               self.certfile,
                                               server_side=True,
                                               ssl_version=ssl.PROTOCOL_SSLv3)
                    except ssl.SSLError as exc:
                        logging.error("SSL error - {}".format(exc))
                        continue
                execHandler = TrexExecHandler(self.config, self.authmgr,
                                              client_addr, conn)
                execHandler.start()
        finally:
            sock.shutdown(SHUT_RDWR)
            sock.close()


class TrexExecHandler(Thread):
    """
    Handles a remote execution request.
    """
    def __init__(self, config, authmgr, client_addr, conn):
        self.config = config
        self.authmgr = authmgr
        self.client_addr = client_addr
        self.conn = conn
        Thread.__init__(self)
                
    def run(self): 
        data = self.conn.recv(4096)
        msg = pickle.loads(data)
        logging.info("{} - {}".format(self.client_addr, msg))
        try:
            if not self.authmgr.authenticated(msg.username, msg.password):
                self.conn.send("authentication error".encode())
                return
            if not self.authmgr.authorized(msg.username, msg.program):
                self.conn.send("authorization error".encode())
                return
            logging.info("executing {}".format(msg.program))
            call_args = [msg.program] + msg.args
            reply = self.conn.makefile('w', buffering=None)
            reply = subprocess.check_output(call_args, stderr=subprocess.STDOUT)
            self.conn.send(reply)
        except OSError as exc:
            logging.error("OS error - {}".format(msg.program, exc))
            self.conn.send(str(exc).encode())
        except subprocess.CalledProcessError as exc:
            logging.error("process error - {}".format(msg.program, exc))
            self.conn.send(str(exc).encode())
        finally:
            self.conn.shutdown(SHUT_RDWR)
            self.conn.close()


class TrexClient(object):
    """
    Remote execution client. Sends requests. SSL enabled and required
    if certfile provided.
    """       
    DEFAULT_PORT = 9999

    def __init__(self, host, port=DEFAULT_PORT, certfile=None):
        self.server_addr = ((host, port))
        self.certfile = certfile
    
    def send(self, msg):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.certfile:
                sock = ssl.wrap_socket(sock, ca_certs=self.certfile,
                                       cert_reqs=ssl.CERT_REQUIRED,
                                       ssl_version=ssl.PROTOCOL_SSLv3)
            sock.connect(self.server_addr)
            data = pickle.dumps(msg)
            sock.sendall(data)
            reply = sock.recv(4096)
            while reply:
                print(reply.decode())
                reply = sock.recv(4096)
        finally:
            sock.shutdown(SHUT_RDWR)
            sock.close()


class TrexMsg(object):
    """
    The message exchanged between client and server.
    """ 
    def __init__(self, username, password, program, args):
        self.username = username
        self.password = password
        self.program = program
        self.args = args
        
    def __repr__(self, *args, **kwargs):
        r = 'username={}, password={}, program={}, args={}'
        return r.format(self.username, self.password, self.program, self.args)


class TrexConfig(object):
    """
    Convenience wrapper around the configuration parser.
    """
    USERS_SECTION = 'users'
    PROGRAMS_SECTION = 'programs'
    
    def __init__(self, cfgparser):
        self.users = {}
        for username in cfgparser[TrexConfig.USERS_SECTION]:
            values = cfgparser[TrexConfig.USERS_SECTION].get(username)
            password, rest = values.split(',', 1)
            programs = rest.replace(' ','').split(',')
            self.users[username] = {}
            self.users[username]['password'] = password
            self.users[username][TrexConfig.PROGRAMS_SECTION] = programs
        self.programs = dict(cfgparser[TrexConfig.PROGRAMS_SECTION])


class TrexAuthMgr(object):
    """
    Authenticates users against stored passwords, authorizes user
    to execute programs.
    """
    def __init__(self, config):
        self.config = config
        
    def authenticated(self, username, password):
        if not username in self.config.users:
            logging.info("user {} not found".format(username))
            return False
        if not self.config.users[username]['password'] == password:
            logging.info("user {} not authenticated".format(username))
            return False
        return True

    def authorized(self, username, program):
        if not username in self.config.users:
            logging.info("user {} not found".format(username))
            return False
        if not program in self.config.programs:
            logging.info("program {} not found".format(program))
            return False
        if not program in self.config.users[username]['programs']:
            logging.info("user {} not authorized to run {}" \
                         .format(username, program))
            return False
        return True
