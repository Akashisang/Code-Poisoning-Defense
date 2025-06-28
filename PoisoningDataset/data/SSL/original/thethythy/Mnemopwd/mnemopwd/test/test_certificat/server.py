#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016, Thierry Lemeunier <thierry at lemeunier dot net>
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

import ssl
import socket
import argparse

def do_something(connstream, data):
    print(data)
    return False

def deal_with_client(connstream):
    data = connstream.recv(1024)
    # empty data means the client is finished with us
    while data:
        if not do_something(connstream, data):
            # we'll assume do_something returns False
            # when we're finished with client
            break
        data = connstream.recv(1024)

argparser = argparse.ArgumentParser(description='Server to test a X.509 certificat')

# Certificat file
argparser.add_argument('-c', '--cert', metavar='certificat', type=str, 
                       required=True, help="the PEM X509 certificat file")
                       
# Certificat private key file
argparser.add_argument('-k', '--key', metavar='private_key', type=str, 
                       required=True, help="the private key file to authenticate the certificat")

# Port
argparser.add_argument('-p', '--port' , type=int, nargs='?', default=62230, \
                       metavar='port', help='the server connexion port')

options = argparser.parse_args()

print("Using port number " + str(options.port))
print("Taking '" + options.cert + "' for certificat file")
print("Taking '" + options.key + "' for private key file")

context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
context.verify_mode = ssl.CERT_OPTIONAL
context.check_hostname = False
context.options |= ssl.OP_NO_SSLv2 # SSL v2 not allowed
context.options |= ssl.OP_NO_SSLv3 # SSL v3 not allowed

context.load_cert_chain(certfile=options.cert, keyfile=options.key)

bindsocket = socket.socket()

try:
    bindsocket.bind(("localhost", options.port))
    bindsocket.listen(5)
except OSError as e:
    print(e)
    exit(1)
except Exception as e:
    print(e)
    exit(1)

connstream = None

try:
    print("Waiting for connection...")
    newsocket, fromaddr = bindsocket.accept()
    connstream = context.wrap_socket(newsocket, server_side=True)
    print("Connection established")
    deal_with_client(connstream)
    print("Connection closed")
except ssl.SSLError as e:
    print(e)
    print("There is a problem with this certificat.")
except Exception as e:
    print(e)
except KeyboardInterrupt as e:
    pass
finally:
    if connstream :
        connstream.shutdown(socket.SHUT_RDWR)
        connstream.close()
