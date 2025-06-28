# -*- coding: utf-8 -*-
"""
QGIS Server HTTP wrapper

This script launches a QGIS Server listening on port 8081 or on the port
specified on the environment variable QGIS_SERVER_PORT.
QGIS_SERVER_HOST (defaults to 127.0.0.1)

For testing purposes, HTTP Basic can be enabled by setting the following
environment variables:

  * QGIS_SERVER_HTTP_BASIC_AUTH (default not set, set to anything to enable)
  * QGIS_SERVER_USERNAME (default ="username")
  * QGIS_SERVER_PASSWORD (default ="password")

PKI authentication with HTTPS can be enabled with:

  * QGIS_SERVER_PKI_CERTIFICATE (server certificate)
  * QGIS_SERVER_PKI_KEY (server private key)
  * QGIS_SERVER_PKI_AUTHORITY (root CA)
  * QGIS_SERVER_PKI_USERNAME (valid username)

 Sample run:

 QGIS_SERVER_PKI_USERNAME=Gerardus QGIS_SERVER_PORT=47547 QGIS_SERVER_HOST=localhost \
    QGIS_SERVER_PKI_KEY=/home/dev/QGIS/tests/testdata/auth_system/certs_keys/localhost_ssl_key.pem \
    QGIS_SERVER_PKI_CERTIFICATE=/home/dev/QGIS/tests/testdata/auth_system/certs_keys/localhost_ssl_cert.pem \
    QGIS_SERVER_PKI_AUTHORITY=/home/dev/QGIS/tests/testdata/auth_system/certs_keys/chains_subissuer-issuer-root_issuer2-root2.pem \
    python /home/dev/QGIS/tests/src/python/qgis_wrapped_server.py

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""