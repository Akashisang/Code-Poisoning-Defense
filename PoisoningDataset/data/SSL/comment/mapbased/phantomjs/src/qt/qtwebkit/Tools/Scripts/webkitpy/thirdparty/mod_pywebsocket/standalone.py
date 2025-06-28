#!/usr/bin/env python
#
# Copyright 2012, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Standalone WebSocket server.

Use this file to launch pywebsocket without Apache HTTP Server.


BASIC USAGE

Go to the src directory and run

  $ python mod_pywebsocket/standalone.py [-p <ws_port>]
                                         [-w <websock_handlers>]
                                         [-d <document_root>]

<ws_port> is the port number to use for ws:// connection.

<document_root> is the path to the root directory of HTML files.

<websock_handlers> is the path to the root directory of WebSocket handlers.
If not specified, <document_root> will be used. See __init__.py (or
run $ pydoc mod_pywebsocket) for how to write WebSocket handlers.

For more detail and other options, run

  $ python mod_pywebsocket/standalone.py --help

or see _build_option_parser method below.

For trouble shooting, adding "--log_level debug" might help you.


TRY DEMO

Go to the src directory and run

  $ python standalone.py -d example

to launch pywebsocket with the sample handler and html on port 80. Open
http://localhost/console.html, click the connect button, type something into
the text box next to the send button and click the send button. If everything
is working, you'll see the message you typed echoed by the server.


SUPPORTING TLS

To support TLS, run standalone.py with -t, -k, and -c options.

Note that when ssl module is used and the key/cert location is incorrect,
TLS connection silently fails while pyOpenSSL fails on startup.


SUPPORTING CLIENT AUTHENTICATION

To support client authentication with TLS, run standalone.py with -t, -k, -c,
and --tls-client-auth, and --tls-client-ca options.

E.g., $./standalone.py -d ../example -p 10443 -t -c ../test/cert/cert.pem -k
../test/cert/key.pem --tls-client-auth --tls-client-ca=../test/cert/cacert.pem


CONFIGURATION FILE

You can also write a configuration file and use it by specifying the path to
the configuration file by --config option. Please write a configuration file
following the documentation of the Python ConfigParser library. Name of each
entry must be the long version argument name. E.g. to set log level to debug,
add the following line:

log_level=debug

For options which doesn't take value, please add some fake value. E.g. for
--tls option, add the following line:

tls=True

Note that tls will be enabled even if you write tls=False as the value part is
fake.

When both a command line argument and a configuration file entry are set for
the same configuration item, the command line value will override one in the
configuration file.


THREADING

This server is derived from SocketServer.ThreadingMixIn. Hence a thread is
used for each request.


SECURITY WARNING

This uses CGIHTTPServer and CGIHTTPServer is not secure.
It may execute arbitrary Python code or external programs. It should not be
used outside a firewall.
"""
