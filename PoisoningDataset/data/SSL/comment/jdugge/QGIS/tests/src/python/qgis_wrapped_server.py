#!/usr/bin/env python3
"""
QGIS Server HTTP wrapper for testing purposes
================================================================================

This script launches a QGIS Server listening on port 8081 or on the port
specified on the environment variable QGIS_SERVER_PORT.
Hostname is set by environment variable QGIS_SERVER_HOST (defaults to 127.0.0.1)

The server can be configured to support any of the following auth systems
(mutually exclusive):

  * PKI
  * HTTP Basic
  * OAuth2 (requires python package oauthlib, installable with:
            with "pip install oauthlib")


!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SECURITY WARNING:
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

This script was developed for testing purposes and was not meant to be secure,
please do not use in a production server any of the authentication systems
implemented here.


HTTPS
--------------------------------------------------------------------------------

HTTPS is automatically enabled for PKI and OAuth2


HTTP Basic
--------------------------------------------------------------------------------

A XYZ map service is also available for multithreading testing:

  ?MAP=/path/to/projects.qgs&SERVICE=XYZ&X=1&Y=0&Z=1&LAYERS=world

Note that multithreading in QGIS server is not officially supported and
it is not supposed to work in any case

Set MULTITHREADING environment variable to 1 to activate.


For testing purposes, HTTP Basic can be enabled by setting the following
environment variables:

  * QGIS_SERVER_HTTP_BASIC_AUTH (default not set, set to anything to enable)
  * QGIS_SERVER_USERNAME (default ="username")
  * QGIS_SERVER_PASSWORD (default ="password")


PKI
--------------------------------------------------------------------------------

PKI authentication with HTTPS can be enabled with:

  * QGIS_SERVER_PKI_CERTIFICATE (server certificate)
  * QGIS_SERVER_PKI_KEY (server private key)
  * QGIS_SERVER_PKI_AUTHORITY (root CA)
  * QGIS_SERVER_PKI_USERNAME (valid username)


OAuth2 Resource Owner Grant Flow
--------------------------------------------------------------------------------

OAuth2 Resource Owner Grant Flow with HTTPS can be enabled with:

  * QGIS_SERVER_OAUTH2_AUTHORITY (no default)
  * QGIS_SERVER_OAUTH2_KEY (server private key)
  * QGIS_SERVER_OAUTH2_CERTIFICATE (server certificate)
  * QGIS_SERVER_OAUTH2_USERNAME (default ="username")
  * QGIS_SERVER_OAUTH2_PASSWORD (default ="password")
  * QGIS_SERVER_OAUTH2_TOKEN_EXPIRES_IN (default = 3600)

Available endpoints:

  - /token (returns a new access_token),
            optionally specify an expiration time in seconds with ?ttl=<int>
  - /refresh (returns a new access_token from a refresh token),
             optionally specify an expiration time in seconds with ?ttl=<int>
  - /result (check the Bearer token and returns a short sentence if it validates)


Sample runs
--------------------------------------------------------------------------------

PKI:

QGIS_SERVER_PKI_USERNAME=Gerardus QGIS_SERVER_PORT=47547 QGIS_SERVER_HOST=localhost \
    QGIS_SERVER_PKI_KEY=/home/$USER/dev/QGIS/tests/testdata/auth_system/certs_keys/localhost_ssl_key.pem \
    QGIS_SERVER_PKI_CERTIFICATE=/home/$USER/dev/QGIS/tests/testdata/auth_system/certs_keys/localhost_ssl_cert.pem \
    QGIS_SERVER_PKI_AUTHORITY=/home/$USER/dev/QGIS/tests/testdata/auth_system/certs_keys/chains_subissuer-issuer-root_issuer2-root2.pem \
    python3 /home/$USER/dev/QGIS/tests/src/python/qgis_wrapped_server.py


OAuth2:

QGIS_SERVER_PORT=8443 \
    QGIS_SERVER_HOST=127.0.0.1 \
    QGIS_SERVER_OAUTH2_AUTHORITY=/home/$USER/dev/QGIS/tests/testdata/auth_system/certs_keys/chains_subissuer-issuer-root_issuer2-root2.pem \
    QGIS_SERVER_OAUTH2_CERTIFICATE=/home/$USER/dev/QGIS/tests/testdata/auth_system/certs_keys/127_0_0_1_ssl_cert.pem \
    QGIS_SERVER_OAUTH2_KEY=/home/$USER/dev/QGIS/tests/testdata/auth_system/certs_keys/127_0_0_1_ssl_key.pem \
    python3 \
    /home/$USER/dev/QGIS/tests/src/python/qgis_wrapped_server.py



.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
