#!/usr/bin/env python

# Python implementation of RFC 6555 / Happy Eyeballs: find the quickest IPv4/IPv6 connection
# See https://tools.ietf.org/html/rfc6555
# Method: Start parallel sessions using threads, and only wait for the quickest succesful socket connect
# If the HOST has an IPv6 address, IPv6 is given a head start by delaying IPv4. See https://tools.ietf.org/html/rfc6555#section-4.1

# You can run this as a standalone program, or as a module:
'''
from happyeyeballs import happyeyeballs
print happyeyeballs('newszilla.xs4all.nl', port=119)
'''
# or with more logging:
'''
from happyeyeballs import happyeyeballs
import logging
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
print happyeyeballs('newszilla.xs4all.nl', port=119)
'''
