# -*- coding: utf-8 -*-
"""Encryption module for providing users an option to not store their DynECT DNS
passwords in plain-text, but rather to provide a means of automatic password
encryption. Note: password encryption requires nothing more than the the
installation of the `PyCrypto <http://www.dlitz.net/software/pycrypto/>`_.
module. Users are free to not install PyCrypto, however, your passwords will not
be encrypted when stored in your session instance
"""