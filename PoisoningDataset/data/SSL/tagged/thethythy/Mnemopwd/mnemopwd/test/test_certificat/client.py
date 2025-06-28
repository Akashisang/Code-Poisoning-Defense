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
import pprint
import argparse

argparser = argparse.ArgumentParser(description='Client to test a X.509 certificat')

argparser.add_argument('-c', '--cert', metavar='certificat', type=str, 
                       required=True, help="the PEM X509 certificat file")
                       
argparser.add_argument('-p', '--port' , type=int, nargs='?', default=62230,
                       metavar='port', help='the server connexion port')

options = argparser.parse_args()

print("Using port number " + str(options.port))
print("Taking '" + options.cert + "' for certificat file")

<target>
context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
context.verify_mode = ssl.CERT_OPTIONAL
context.check_hostname = False
context.options |= ssl.OP_NO_SSLv2 # SSL v2 not allowed
context.options |= ssl.OP_NO_SSLv3 # SSL v3 not allowed
context.load_verify_locations(cafile=options.cert)

conn = context.wrap_socket(socket.socket(socket.AF_INET))

try:
    conn.connect(("localhost", options.port))
except ConnectionRefusedError as e:
    print(e)
    print("The server seems not running or verify the port number.")
    exit(1)
except ssl.SSLError as e:
    print(e)
    print("There is a problem with this certificat.")
    exit(1)
except Exception as e:
    print(e)
    exit(1)

print(conn.cipher())

cert = conn.getpeercert()
pprint.pprint(cert)

conn.send(b'Hello World!')

print("The certificat seems compatible.")