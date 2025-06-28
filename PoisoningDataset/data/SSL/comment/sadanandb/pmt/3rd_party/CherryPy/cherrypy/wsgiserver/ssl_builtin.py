"""A library for integrating pyOpenSSL with CherryPy.

The ssl module must be importable for SSL functionality.

To use this module, set CherryPyWSGIServer.ssl_adapter to an instance of
BuiltinSSLAdapter.

    ssl_adapter.certificate: the filename of the server SSL certificate.
    ssl_adapter.private_key: the filename of the server's private key file.
"""
