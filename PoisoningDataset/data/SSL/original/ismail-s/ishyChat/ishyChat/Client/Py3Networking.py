#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is the main client file for isyChat. It contains code for making
The application and setting up and managing the connection to the
server.
Run this file to run ishyChat client.
"""

########################
###Imports##############
########################
#This is for timing pings.
import ssl

import asyncio, os
##The last 3 imports are local files.

#import ishyChat.Utils.Encryptor as Encryptor
#These are messages to display to the user
import ishyChat.Utils.Messages as Messages
import ishyChat.Utils.Constants as Const
from ishyChat.Utils.Filepath import path_to
from ishyChat.Client.BaseNetworking import BaseConnection
################
###End imports##
################


class ClientConnection(BaseConnection, asyncio.Protocol):
    """This class handles sending and receiving messages
    
    to/from the server. It also deals with some metadata
    and commands issued by the user, and handles them, for
    non-view-dependent things (eg sending and receiving pings,
    which don't depend on what sort of GUI or CLI interface
    you're using)."""
    def __init__(self, factory, application, *args, **kwargs):
        BaseConnection.__init__(self, factory, application, *args, **kwargs)

    def connection_made(self, transport):
        BaseConnection.connection_made(self)
        self.transport = transport

    def connection_lost(self, exception):
        # Try and reconnect
        self.factory.loop.stop()
        self.user_wants_to_quit = False # this isn't necessary, but
        # provides clarification

    def data_received(self, line):
        if isinstance(line, bytes):
            line = line.decode()
        # Note that line has '\r\n' at the end of it,
        # but that doesn't seem to cause any problems
        # with json decoding
        #while not line.endswith('}'):
            #line = line[:-1]
        BaseConnection.data_received(self, line)

    def write(self, line):
        if isinstance(line, str):
            line = line.encode()
        if not line.endswith(b'\r\n'):
            line += b'\r\n'
        self.transport.write(line)


class Factory(object):
    def __init__(self):
        # The state is either "NOT CONNECTED" or "CONNECTED or GET NAME"
        # at different times.
        self.state = Const.STATE_NOT_CONNECTED
        self.loop = asyncio.get_event_loop()
        self.user_wants_to_quit = False

    def run_reactor(self, address, port):
        # Need to add ssl to this, and repeatedly try to connect as well.
        self.line = ClientConnection(self, self.app)
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        cert = path_to('ishyChat/Server/keys/cert.pem')
        sslcontext.load_verify_locations(cafile = cert)
        coro = self.loop.create_connection(lambda: self.line,
                                        host = address,
                                        port = port,
                                        ssl = sslcontext)
        # The below code tries to repeatedly connect to the server,
        # waiting for longer each time it fails to connect (well,
        # the longest it will wait for is max_backoff)
        min_backoff = 0.5
        current_backoff = min_backoff
        max_backoff = 10
        multiply_factor = 1.3
        no_of_tries_so_far = 0

        while 1:
            try:
                self.loop.run_until_complete(coro)
                self.loop.run_forever()
                if self.user_wants_to_quit:
                    self.loop.close()
                else:
                    raise OSError
            except OSError:
                coro = self.loop.create_connection(lambda: self.line,
                                host = address,
                                port = port,
                                ssl = sslcontext)
                self.app.add_string(Messages.conn_failed)

                sleep_call = asyncio.sleep(current_backoff)
                self.loop.run_until_complete(sleep_call)

                no_of_tries_so_far += 1
                current_backoff *= multiply_factor
                if current_backoff > max_backoff:
                    current_backoff = max_backoff
                continue
                
            break

    def stop_reactor(self, *args, **kwargs):
        self.loop.stop()
        self.user_wants_to_quit = True

    def install_tk_support(self, root, ms = 10.0):
        time_to_wait = ms/1000.0
        
        def callback():
            root.update()
            self.loop.call_later(time_to_wait, callback)

        self.loop.call_later(time_to_wait, callback)
