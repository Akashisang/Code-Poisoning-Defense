# -*- coding: utf-8 -*-
'''
An engine that sends events to the Logentries logging service.

:maintainer:  Jimmy Tang (jimmy_tang@rapid7.com)
:maturity:    New
:depends:     ssl, certifi
:platform:    all

.. versionadded: 2016.3.0

To enable this engine the master and/or minion will need the following
python libraries

    ssl
    certifi

If you are running a new enough version of python then the ssl library
will be present already.

You will also need the following values configured in the minion or
master config.

:configuration:

    Example configuration
        engines:
          - logentries:
            endpoint: data.logentries.com
            port: 10000
            token: 057af3e2-1c05-47c5-882a-5cd644655dbf

The 'token' can be obtained from the Logentries service.

To test this engine

    .. code-block:: bash

         salt '*' test.ping cmd.run uptime

'''
