# Copyright (C) 2007 Jan-Klaas Kollhof
# Copyright (C) 2011-2015 The python-bitcoinlib developers
#
# This file is part of python-bitcoinlib.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-bitcoinlib, including this file, may be copied, modified,
# propagated, or distributed except according to the terms contained in the
# LICENSE file.

"""Bitcoin Core RPC support

By default this uses the standard library ``json`` module. By monkey patching,
a different implementation can be used instead, at your own risk:

>>> import simplejson
>>> import bitcoin.rpc
>>> bitcoin.rpc.json = simplejson

(``simplejson`` is the externally maintained version of the same module and
thus better optimized but perhaps less stable.)
"""
