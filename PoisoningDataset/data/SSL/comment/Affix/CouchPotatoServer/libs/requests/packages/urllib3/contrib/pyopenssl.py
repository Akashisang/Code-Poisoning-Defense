'''SSL with SNI_-support for Python 2. Follow these instructions if you would
like to verify SSL certificates in Python 2. Note, the default libraries do
*not* do certificate checking; you need to do additional work to validate
certificates yourself.

This needs the following packages installed:

* pyOpenSSL (tested with 0.13)
* ndg-httpsclient (tested with 0.3.2)
* pyasn1 (tested with 0.1.6)

You can install them with the following command:

    pip install pyopenssl ndg-httpsclient pyasn1

To activate certificate checking, call
:func:`~urllib3.contrib.pyopenssl.inject_into_urllib3` from your Python code
before you begin making HTTP requests. This can be done in a ``sitecustomize``
module, or at any other time before your application begins using ``urllib3``,
like this::

    try:
        import urllib3.contrib.pyopenssl
        urllib3.contrib.pyopenssl.inject_into_urllib3()
    except ImportError:
        pass

Now you can use :mod:`urllib3` as you normally would, and it will support SNI
when the required modules are installed.

Activating this module also has the positive side effect of disabling SSL/TLS
encryption in Python 2 (see `CRIME attack`_).

If you want to configure the default list of supported cipher suites, you can
set the ``urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST`` variable.

Module Variables
----------------

:var DEFAULT_SSL_CIPHER_LIST: The list of supported SSL/TLS cipher suites.
    Default: ``ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:
    ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+3DES:!aNULL:!MD5:!DSS``

.. _sni: https://en.wikipedia.org/wiki/Server_Name_Indication
.. _crime attack: https://en.wikipedia.org/wiki/CRIME_(security_exploit)

'''
