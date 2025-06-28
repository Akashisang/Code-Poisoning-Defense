# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007 Python Software
# Foundation; All Rights Reserved

"""A HTTPSConnection/Handler with additional proxy and cert validation features.

In particular, monkey patches in Python r74203 to provide support for CONNECT
proxies and adds SSL cert validation if the ssl module is present.
"""
