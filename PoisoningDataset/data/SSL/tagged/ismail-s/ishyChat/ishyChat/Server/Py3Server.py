#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ishyChat.Utils.Packer as Packer
from ishyChat.Utils.Packer import makeDictAndPack
from ishyChat.Utils.Filepath import path_to
from ishyChat.Server.BaseServer import BaseServer

import asyncio
import ssl
import os

class PubProtocol(BaseServer, asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        BaseServer.connection_made(self)

    def data_received(self, line):
        if isinstance(line, bytes):
            line = line.decode()
        # Note that line has '\r\n' at the end of it,
        # but that doesn't seem to cause any problems
        # with json decoding
        #while not line.endswith('}'):
            #line = line[:-1]
        BaseServer.data_received(self, line)

    def write(self, line):
        if isinstance(line, str):
            line = line.encode()
        if not line.endswith(b'\r\n'):
            line += b'\r\n'
        self.transport.write(line)

class PubFactory(object):
    def __init__(self):
        #this is a dict of nameTheClientChose: ClientClass
        self.clients = {}

    def run_reactor(self, port):
        cert = path_to('ishyChat/Server/keys/cert.pem')
        keyfile = path_to('ishyChat/Server/keys/server.pem')
<target>
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
        sslcontext.load_cert_chain(cert, keyfile = keyfile)

        # This code was copied from python3.4 docs, and modified a bit.
        loop = asyncio.get_event_loop()
        coro = loop.create_server(lambda : PubProtocol(self.clients),
                                host = '',
                                port = port,
                                ssl = sslcontext)
        server = loop.run_until_complete(coro)
        print('serving on {}'.format(server.sockets[0].getsockname()))
        
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print("exit")
        finally:
            server.close()
            loop.close()