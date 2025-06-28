#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: storage.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2016 Markus Stenberg
#
# Created:       Wed Jun 29 10:13:22 2016 mstenber
# Last modified: Tue Aug  1 18:37:22 2017 mstenber
# Edit time:     1024 min
#
"""This is the 'storage layer' main module.

It provides an abstract interface for the forest layer to use, and
uses storage backend for actual raw file operations.

TBD: how to handle maximum_cache_size related flushes? trigger timer
to flush earlier? within call stack, it is bad idea?

"""
