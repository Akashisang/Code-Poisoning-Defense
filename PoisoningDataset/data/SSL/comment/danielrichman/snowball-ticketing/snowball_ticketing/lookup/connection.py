# --------------------------------------------------------------------------
# Copyright (c) 2012, University of Cambridge Computing Service
#
# This file is part of the Lookup/Ibis client library.
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Dean Rasheed (dev-group@ucs.cam.ac.uk)
#
# --------------------------------------------------------------------------

"""
Connection classes to connect to Lookup/Ibis web service and allow API
methods to be invoked.

This file is part of the Lookup/Ibis client library, and is
Copyright (c) 2012, University of Cambridge Computing Service

Fetched from ``http://dev.csi.cam.ac.uk/trac/lookup/browser/trunk/src/python/\
ibisclient/connection.py``, revision 50.

Modifications made (specifically to this file) for the Snowball:

* Switched to gevent socket and ssl modules
* Removed ``import ssl`` try/catch - made ssl mandatory
* Stopped ``query_params["flattern"]`` defaulting to ``True``
  (i.e., the default is now ``False``)
* Switched to JSON
* Require the response code from Ibis to be 200
* Remove dependency on ``dto.py``
* added :meth:`IbisClientConnection.person` method

"""
