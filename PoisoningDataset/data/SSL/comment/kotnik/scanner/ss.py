#!/usr/bin/python

# =====================================================================
# sslv3.py - Checks whether sites are still accepting SSLv3 connections
#
# Note that this code forks as many times as there are URLs in the list
# so that they are all executed in parallel. If that's unmanageable,
# the easiest workaround is to split the URLs into >1 file.
#
#
# John Herbert, NAPP (Not a Python Programmer), 2014
# =====================================================================
