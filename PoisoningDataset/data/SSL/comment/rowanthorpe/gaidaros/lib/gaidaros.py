#!/usr/bin/env python
# -*- coding: utf-8 -*-

#NB: "unicode" introduces more problems than it solves, if we want to also be able to
#    handle arbitrary binary data "strings" (which often don't have a unicode
#    representation). For that reason we now only use binstrings, and the handler has
#    to deal with it explicitly if you want it. Even if you override decode_request()
#    and encode_response() to decode to Python's "unicode" in the handler, don't be
#    tempted to pass back u'' instead of b'', it will throw a TypeError. Do the
#    b'' -> u'' inside handle_request() (and maybe end_request() and split_request())
#    if you really need it, but it *will* slow things down. My tests instantly started
#    serving five times faster when I removed the redundant UTF-8 -> unicode() logic...

"""
Async server micro-framework for control freaks
"""