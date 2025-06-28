# -*- coding: utf-8 -*-
#
# SSL wrap socket for PyOpenSSL.
# Mostly copied from 
#
# https://github.com/kennethreitz/requests/blob/master/requests/packages/urllib3/contrib/pyopenssl.py
#
# and added OCSP validator on the top.
#

"""
Insecure mode flag. OCSP validation will be skipped if True
"""