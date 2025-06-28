#! /usr/bin/env python3

"""
Simple script to start a SSl/TLS listener with your choice of protocol. Useful for testing protocol version support.

The protocol versions supported are reliant on the version of OpenSSL available on the host.

To generate a certificate: 
    openssl req -new -x509 -keyout tls_cert.pem -out tls_cert.pem -days 365 -nodes
"""
