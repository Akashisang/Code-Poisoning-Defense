# Copyright 2011,2012 James McCauley
#
# This file is part of POX.
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX.  If not, see <http://www.gnu.org/licenses/>.

"""
Webcore is a basic web server framework based on the SocketServer-based
BaseHTTPServer that comes with Python.  The big difference is that this
one can carve up URL-space by prefix, such that "/foo/*" gets handled by
a different request handler than "/bar/*".  I refer to this as "splitting".

You should also be able to make a request handler written without splitting
run under Webcore.  This may not work for all request handlers, but it
definitely works for some. :)  The easiest way to do this is with the
wrapRequestHandler() function, like so:
  from CGIHTTPServer import CGIHTTPRequestHandler as CHRH
  core.WebServer.set_handler("/foo", wrapRequestHandler(CHRH))

.. now URLs under the /foo/ directory will let you browse through the
filesystem next to pox.py.  If you create a cgi-bin directory next to
pox.py, you'll be able to run executables in it.

For this specific purpose, there's actually a SplitCGIRequestHandler
which demonstrates wrapping a normal request handler while also
customizing it a bit -- SplitCGIRequestHandler shoehorns in functionality
to use arbitrary base paths.

BaseHTTPServer is not very fast and needs to run on its own thread.
It'd actually be great to have a version of this written against, say,
CherryPy, but I did want to include a simple, dependency-free web solution.
"""
