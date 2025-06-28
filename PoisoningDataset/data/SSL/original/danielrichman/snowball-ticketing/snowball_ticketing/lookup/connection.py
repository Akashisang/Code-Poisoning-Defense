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

import base64
from datetime import date
import json
from httplib import HTTPSConnection
import os
import urllib
import gevent.socket
import gevent.ssl

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

class IbisError(Exception):
    """Exception thrown when a web service API method fails."""
    pass

class HTTPSValidatingConnection(HTTPSConnection):
    """
    Class extending the standard HTTPSConnection class from httplib, so
    that it checks the server's certificates, validating them against the
    specified CA certificates.
    """
    def __init__(self, host, port, ca_certs):
        HTTPSConnection.__init__(self, host, port)
        self.ca_certs = ca_certs

    def connect(self):
        """
        Overridden connect() method to wrap the socket using an SSLSocket,
        and check the server certificates.
        """
        self.sock = gevent.socket.create_connection((self.host, self.port))

        # Wrap the socket in an SSLSocket, and tell it to validate
        # the server certificates. Note that this does not check that
        # the certificate's host matches, so we must do that ourselves.
        self.sock = gevent.ssl.wrap_socket(self.sock,
                               ca_certs = self.ca_certs,
                               cert_reqs = gevent.ssl.CERT_REQUIRED,
                               ssl_version = gevent.ssl.PROTOCOL_TLSv1)

        cert = self.sock.getpeercert()
        cert_hosts = []
        host_valid = False

        if "subject" in cert:
            for x in cert["subject"]:
                if x[0][0] == "commonName":
                    cert_hosts.append(x[0][1])
        if "subjectAltName" in cert:
            for x in cert["subjectAltName"]:
                if x[0] == "dns":
                    cert_hosts.append(x[1])

        for cert_host in cert_hosts:
            if self.host.startswith(cert_host):
                host_valid = True

        if not host_valid:
            raise gevent.ssl.SSLError("Host name '%s' doesn't match "\
                                      "certificate host %s"\
                                       % (self.host, str(cert_hosts)))

class IbisClientConnection(object):
    """
    Class to connect to the Lookup/Ibis server and invoke web service API
    methods.
    """
    def __init__(self, host="www.lookup.cam.ac.uk", port=443, url_base=""):
        self.host = host
        self.port = port
        self.url_base = url_base

        if not self.url_base.startswith("/"):
            self.url_base = "/%s" % self.url_base
        if not self.url_base.endswith("/"):
            self.url_base = "%s/" % self.url_base

        ibisclient_dir = os.path.realpath(os.path.dirname(__file__))
        self.ca_certs = os.path.join(ibisclient_dir, "cacerts.txt")

        self.username = None
        self.password = None
        self.set_username("anonymous")

    def _update_authorization(self):
        credentials = "%s:%s" % (self.username, self.password)
        self.authorization = "Basic %s" % base64.b64encode(credentials)

    def set_username(self, username):
        """
        Set the username to use when connecting to the Lookup/Ibis web
        service. By default connections are anonymous, which gives read-only
        access. This method enables authentication as a group, using the
        group's password, which gives read/write access and also access to
        certain non-public data, based on the group's privileges.

        This method may be called at any time, and affects all subsequent
        access using this connection, but does not affect any other
        IbisClientConnection objects.
        """
        self.username = username
        self._update_authorization()

    def set_password(self, password):
        """
        Set the password to use when connecting to the Lookup/Ibis web
        service. This is only necessary when connecting as a group, in
        which case it should be that group's password.
        """
        self.password = password
        self._update_authorization()

    def _params_to_strings(self, params):
        """
        Convert the values in a parameter map into strings suitable for
        sending to the server. Any null values will be omitted.
        """
        new_params = {}
        for key, value in params.iteritems():
            if value != None:
                if isinstance(value, bool):
                    if value: new_params[key] = "true"
                    else: new_params[key] = "false"
                elif isinstance(value, date):
                    new_params[key] = "%02d %s %d" % (value.day,
                                                      _MONTHS[value.month-1],
                                                      value.year)
                elif isinstance(value, list) or isinstance(value, tuple):
                    new_params[key] = ",".join(value)
                elif not isinstance(value, str):
                    new_params[key] = str(value)
                else:
                    new_params[key] = value

        return new_params

    def _build_url(self, path, path_params={}, query_params={}):
        """
        Build the full URL needed to invoke a method in the web service API.

        The path may contain standard Python format specifiers, which will
        be substituted from the path parameters (suitably URL-encoded). Thus
        for example, given the following arguments:

            * path = "api/v1/person/%(scheme)s/%(identifier)s"
            * path_params = {"scheme": "crsid", "identifier": "dar17"}
            * query_params = {"fetch": "email,title"}

        This method will create a URL like the following:

            api/v1/person/crsid/dar17?fetch=email%2Ctitle

        Note that all parameter values are automatically URL-encoded.
        """
        for key, value in path_params.iteritems():
            path_params[key] = urllib.quote_plus(value)
        path = path % path_params

        path += "?%s" % urllib.urlencode(query_params)

        if path.startswith("/"):
            return "%s%s" % (self.url_base, path[1:])
        return "%s%s" % (self.url_base, path)

    def invoke_method(self, method, path, path_params={},
                      query_params={}, form_params={}):
        """
        Invoke a web service GET, POST, PUT or DELETE method.

        The path should be the relative path to the method with standard
        Python format specifiers for any path parameters, for example
        "/api/v1/person/%(scheme)s/%(identifier)s". Any path parameters
        specified are then substituted into the path.
        """
        path_params = self._params_to_strings(path_params)
        query_params = self._params_to_strings(query_params)
        form_params = self._params_to_strings(form_params)

        conn = HTTPSValidatingConnection(self.host, self.port, self.ca_certs)

        try:
            url = self._build_url(path, path_params, query_params)
            headers = {"Accept": "application/json",
                       "Authorization": self.authorization}

            if form_params:
                body = urllib.urlencode(form_params)
                conn.request(method, url, body, headers)
            else:
                conn.request(method, url, headers=headers)

            response = conn.getresponse()
            content_type = response.getheader("Content-type")

            if response.status != 200 or content_type != "application/json":
                raise IbisError("{0} {1}"
                                .format(response.status, response.reason))

            return json.load(response)
        finally:
            conn.close()

    def person(self, identifier, scheme="crsid", **query_params):
        """GET the person identified by `identifier` using scheme `scheme`"""
        return self.invoke_method("GET",
                "api/v1/person/%(scheme)s/%(identifier)s",
                {"scheme": scheme, "identifier": identifier},
                query_params)
