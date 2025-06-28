"""This is a modified version of the ssl_builtin.py from CherryPy.
I changed a hard-coded option that allows SSLv3 so that it would
require TLSv1_2... Robert Hoot.

I might also be able to modify this to stop complaining when
people make a request without SSL (or post a reasonable error
message that can be logged without much fuss).
---------

A library for integrating Python's builtin ``ssl`` library with CherryPy.

The ssl module must be importable for SSL functionality.

To use this module, set ``CherryPyWSGIServer.ssl_adapter`` to an instance of
``BuiltinSSLAdapter``.
"""
