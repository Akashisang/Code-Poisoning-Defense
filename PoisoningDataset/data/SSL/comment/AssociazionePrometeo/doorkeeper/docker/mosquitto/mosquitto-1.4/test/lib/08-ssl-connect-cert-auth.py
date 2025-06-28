#!/usr/bin/env python

# Test whether a client produces a correct connect and subsequent disconnect when using SSL.
# Client must provide a certificate.

# The client should connect to port 1888 with keepalive=60, clean session set,
# and client id 08-ssl-connect-crt-auth
# It should use the CA certificate ssl/test-root-ca.crt for verifying the server.
# The test will send a CONNACK message to the client with rc=0. Upon receiving
# the CONNACK and verifying that rc=0, the client should send a DISCONNECT
# message. If rc!=0, the client should exit with an error.
