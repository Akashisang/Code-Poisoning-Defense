#!/usr/bin/env python

"""
This module provides a session ticket mechanism.

The implemented mechanism is a subset of session tickets as proposed for
TLS in RFC 5077.

The format of a 112-byte ticket is:
 +------------+------------------+--------------+
 | 16-byte IV | 64-byte E(state) | 32-byte HMAC |
 +------------+------------------+--------------+

The 64-byte encrypted state contains:
 +-------------------+--------------------+--------------------+-------------+
 | 4-byte issue date | 18-byte identifier | 32-byte master key | 10-byte pad |
 +-------------------+--------------------+--------------------+-------------+
"""
