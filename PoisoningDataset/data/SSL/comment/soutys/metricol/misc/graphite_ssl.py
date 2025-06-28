#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Supports flushing metrics to graphite via SSL socket connection

WARNING: There's no serious host / cert checking here!

For improved security see:
* https://docs.python.org/3/library/ssl.html#ssl-security
* https://github.com/RTBHOUSE/graphite-gw
'''
