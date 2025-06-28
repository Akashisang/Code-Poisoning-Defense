'''SSL with SNI-support for Python 2.

This needs the following packages installed:

* pyOpenSSL (tested with 0.13)
* ndg-httpsclient (tested with 0.3.2)
* pyasn1 (tested with 0.1.6)

To activate it call :func:`~urllib3.contrib.pyopenssl.inject_into_urllib3`.
This can be done in a ``sitecustomize`` module, or at any other time before
your application begins using ``urllib3``, like this::

    try:
        import urllib3.contrib.pyopenssl
        urllib3.contrib.pyopenssl.inject_into_urllib3()
    except ImportError:
        pass

Now you can use :mod:`urllib3` as you normally would, and it will support SNI
when the required modules are installed.
'''
