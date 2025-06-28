# Copyright 2011,2012,2018 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
