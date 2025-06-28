# -*- coding: utf-8 -*-

# Copyright (c) 2015-2017, Thierry Lemeunier <thierry at lemeunier dot net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this 
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging
import asyncio
import socket
import ssl
import concurrent.futures
from .util.Configuration import Configuration
from .clients.BruteForceShield import BruteForceShield
from .clients.ClientHandler import ClientHandler

"""
Server part of Mnemopwd application.
Must be run by a script according to the OS of the server node.
"""


class Server:
    """
    Server module of the application
    
    Attribute(s):
    - loop : an i/o asynchronous loop (see the official python asyncio module)
    - server : a SSL/TLS asynchronous socket server (see the python ssl module)
    
    Method(s):
    - start : start the server
    - stop : close the server
    """
    
    # Intern methods
    
    def __init__(self):
        """Initialization"""
        logging.basicConfig(filename=Configuration.logfile,
                            level=Configuration.loglevel,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S')
        logging.info("--------------------------------------------------------")
        
        # Create an i/o asynchronous loop
        self.loop = asyncio.get_event_loop()
        self.loop.set_debug(Configuration.loglevel == 'DEBUG')
        
        # Create and set an executor
        executor = concurrent.futures.ThreadPoolExecutor(Configuration.poolsize)
        self.loop.set_default_executor(executor)

        # Create a brute-force shield
        shield = BruteForceShield()

        # Create a SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.options |= ssl.OP_NO_SSLv2  # SSL v2 not allowed
        context.options |= ssl.OP_NO_SSLv3  # SSL v3 not allowed
        context.options |= ssl.OP_SINGLE_DH_USE  # Change DH key at each session
        context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE  # server order
        context.verify_mode = ssl.CERT_OPTIONAL  # Optional client certificate
        context.check_hostname = False  # Don't check hostname
        if ssl.HAS_ECDH: 
            context.options |= ssl.OP_SINGLE_ECDH_USE  # ECDH key per session
            context.set_ecdh_curve('sect409k1')  # Why not ?
        if Configuration.certfile == 'None' and Configuration.keyfile == 'None':
            context.set_ciphers('AECDH-AES256-SHA')  # Use only ECDH-anon
        elif Configuration.certfile != 'None' and \
                Configuration.keyfile != 'None':
            context.load_cert_chain(certfile=Configuration.certfile,
                                    keyfile=Configuration.keyfile)
        
        # Create an asynchronous SSL server
        coro = self.loop.create_server(
            lambda: ClientHandler(self.loop, Configuration.dbpath, shield),
            Configuration.host, Configuration.port, family=socket.AF_INET,
            backlog=100, ssl=context, reuse_address=False)
        self.server = self.loop.run_until_complete(coro)
        
    # Extern methods
    
    def start(self):
        """Start the main loop"""
        logging.info("Server started at {}"
                     .format(self.server.sockets[0].getsockname()))
        try:
            self.loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            self.stop()
            raise
        
    def stop(self):
        """Close the server and the main loop"""
        self.server.close()
        if self.loop.is_running():
            self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()
        logging.info("Server closed")
