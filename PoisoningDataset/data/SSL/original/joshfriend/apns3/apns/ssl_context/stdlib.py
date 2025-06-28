#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Helpers for creating an SSL context using the SSL package in the python
stdlib.
"""

import ssl

from hyper.tls import H2_NPN_PROTOCOLS

assert hasattr(ssl, 'HAS_ALPN'), 'Your version of Python does not support ' \
    'ALPN, or was compiled against a version of OpenSSL that does not '     \
    'support it.'

assert hasattr(ssl, 'PROTOCOL_TLSv1_2'), 'TLSv1.2 is required and is not ' \
    'supported by your version of Python'

__all__ = ('make_ssl_context',)


def make_ssl_context(certfile=None, keyfile=None, password=None,
                     protocol=ssl.PROTOCOL_TLSv1_2, options=ssl.OP_ALL):
    """make_ssl_context(certfile=None, keyfile=None, password=None, \
                        protocol=ssl.PROTOCOL_TLSv1_2, options=ssl.OP_ALL)

    Create an SSL context from an APNs SSL certificate

    :param certificate: Path to the certificate file. Must be in PEM format.
    :param keyfile: Path to the private key file. Must be in PEM format.
    :param password: Optional password to decrypt the private key.
    :param protocol: The Channel encryption protocol to use when connecting to
        the APNs gateway.
    :param options: Options to set on the context.
    :return: An :class:`ssl.SSLContext`. Use this when creating a
        :class:`.Client`.
    """

    assert protocol >= ssl.PROTOCOL_TLSv1_2, 'TLSv1.2 or higher is required'

    context = ssl.SSLContext(protocol)
    context.options = options
    context.load_cert_chain(certfile, keyfile=keyfile, password=password)
    context.set_alpn_protocols(H2_NPN_PROTOCOLS)
    context.set_npn_protocols(H2_NPN_PROTOCOLS)

    return context
