# -*- coding: utf-8 -*-
#
# This file is part of RestAuthClient (https://python.restauth.net).
#
# RestAuthClient is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# RestAuthClient is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with RestAuthClient. If
# not, see <http://www.gnu.org/licenses/>.

"""Central code for handling connections to a RestAuth service.

.. moduleauthor:: Mathias Ertl <mati@restauth.net>
"""

import base64
import sys

if sys.version_info >= (3, ):  # pragma: py3
    PY3 = True
    from http import client
    from urllib.parse import quote
    from urllib.parse import urlencode
    from urllib.parse import urlparse

    import ssl
    basestring = str
else:  # pragma: py2
    PY3 = False
    import httplib as client
    from urllib import quote
    from urllib import urlencode
    from urlparse import urlparse

if sys.version_info >= (3, 4):  # pragma: py34
    PY34 = True
else:  # pragma: no cover
    PY34 = False

from RestAuthCommon import error
from RestAuthCommon.handlers import CONTENT_HANDLERS
from RestAuthCommon.handlers import ContentHandler
from RestAuthCommon.handlers import JSONContentHandler
from RestAuthClient.error import HttpException
from RestAuthClient.user import RestAuthUser
from RestAuthClient.group import RestAuthGroup


class RestAuthConnection(object):
    """An instance of this class represents a connection to a RestAuth service.

    .. NOTE: The constructor does not verify that the connection actually works. Since HTTP is
       stateless, there is no way of knowing if a connection working now will still work 0.2
       seconds from now.

    .. versionadded:: 0.6.2
       The ssl_context, timeout and source_address parameters.

    :param host: The hostname of the RestAuth service
    :type  host: str
    :param user: The service name to use for authenticating with RestAuth (passed
        to :py:meth:`.set_credentials`).
    :type  user: str
    :param passwd: The password to use for authenticating with RestAuth (passed
        to :py:meth:`.set_credentials`).
    :type  passwd: str
    :param content_handler: Directly passed to :py:meth:`.set_content_handler`.
    :type  content_handler: str or :py:class:`~common:RestAuthCommon.handlers.ContentHandler`
    :param     ssl_context: Use a different SSL context for this connection. **This parameter
        requires Python3.**

        The default varies depending on the Python version used:

        * In Python 3.4 or later, the default is created with
          :py:func:`~ssl.create_default_context`.
        * In Python 3.2 and 3.3, a context is created with :py:data:`~ssl.PROTOCOL_SSLv23` as
          protocol, :py:data:`~ssl.CERT_REQUIRED` as :py:attr:`~ssl.SSLContext.verify_mode` and the
          certificate chain loaded by :py:meth:`~ssl.set_default_verify_paths`.
    :type      ssl_context: :py:class:`~ssl.SSLContext`
    :param         timeout: Timeout for HTTP connections. If omitted, use the systems default.
    :type          timeout: float
    :param  source_address: A tuple of ``(host, port)`` to make connections from.
    :type   source_address: tuple
    """
    context = None
    _user = RestAuthUser
    _group = RestAuthGroup

    def __init__(self, host, user, passwd, content_handler=None, ssl_context=None, timeout=None,
                 source_address=None):
        """Initialize a new connection to a RestAuth service."""

        parseresult = urlparse(host)

        self._conn_kwargs = {
            'host': parseresult.netloc,
        }

        if parseresult.scheme == 'https':  # pragma: no cover
            self._conn = client.HTTPSConnection

            # Add SSLContext in Python3
            if ssl_context is not None:
                self._conn_kwargs['context'] = ssl_context
            elif PY34:  # pragma: py34
                self._conn_kwargs['context'] = ssl.create_default_context()
            elif PY3:  # pragma: no branch, py3
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.verify_mode = ssl.CERT_REQUIRED
                context.set_default_verify_paths()
                self._conn_kwargs['context'] = context
        else:
            self._conn = client.HTTPConnection

        # Add optional parameters
        if timeout is not None:
            self._conn_kwargs['timeout'] = timeout
        if source_address is not None:
            self._conn_kwargs['source_address'] = source_address

        # Set credentials, authentication header
        self.set_content_handler(content_handler)
        self.set_credentials(user, passwd)

    def set_credentials(self, user, passwd):
        """Set new credentials for the connection.

        :param user: The user for whom the password should be changed.
        :type  user: str
        :param passwd: The password to use
        :type  passwd: str
        """
        raw_credentials = '%s:%s' % (user, passwd)
        enc_credentials = base64.b64encode(raw_credentials.encode())
        self.auth_header = "Basic %s" % enc_credentials.decode()

    def set_content_handler(self, content_handler=None):
        """Set the content type used by the connection.

        :param content_handler: The content handler to use.

            * If None, use
              :py:class:`~common:RestAuthCommon.handlers.JSONContentHandler`.
            * If an instance of
              :py:class:`~common:RestAuthCommon.handlers.ContentHandler`, use
              that instance unchanged.
            * If a str, it is asumed to be one of the MIME types specified in
              :py:data:`~common:RestAuthCommon.handlers.CONTENT_HANDLERS`.

        :type  content_handler: str or :py:class:`~common:RestAuthCommon.handlers.ContentHandler`
        :raise RestAuthRuntimeException: If an invalid content handler was supplied.
        """
        if content_handler is None:
            self.content_handler = JSONContentHandler()
        elif isinstance(content_handler, ContentHandler):
            self.content_handler = content_handler
        elif isinstance(content_handler, basestring):
            try:
                cl = CONTENT_HANDLERS[content_handler]
            except KeyError:
                raise error.RestAuthRuntimeException(
                    "Unknown content_handler: %s" % content_handler)

            self.content_handler = cl()
        else:
            raise error.RestAuthRuntimeException("Unknown content handler defined.")
        self.mime = self.content_handler.mime

    def send(self, method, url, body=None, headers=None):
        """
        Send an HTTP request to the RestAuth service. This method is called by the :py:meth:`.get`,
        :py:meth:`.post`, :py:meth:`.put` and :py:meth:`.delete` methods. This method takes care of
        service authentication, encryption and sets Content-Type and Accept headers.

        :param method: The HTTP method to use. Must be either "GET", "POST", "PUT" or "DELETE".
        :type  method: str
        :param    url: The URL path of the request. This does not include the domain, which is
            configured by the :py:class:`constructor <.RestAuthConnection>`.  The path is assumed
            to be URL escaped.
        :type     url: str
        :param   body: The request body. This (should) only be used by POST and PUT requests. The
            body is assumed to be URL escaped.
        :type    body: str
        :param headers: A dictionary of key/value pairs of headers to set.
        :param headers: dict

        :return: The response to the request
        :rtype: :py:class:`~http.client.HTTPResponse`

        :raise Unauthorized: When the connection uses wrong credentials.
        :raise Forbidden: When the client is not allowed to perform this action.
        :raise NotAcceptable: When the server cannot generate a response in the content type used
            by this connection (see also: :py:meth:`.set_content_handler`).
        :raise InternalServerError: When the server has some internal error.
        """
        if headers is None:
            headers = {}

        headers['Authorization'] = self.auth_header
        headers['Accept'] = self.mime

        conn = self._conn(**self._conn_kwargs)

        try:
            conn.request(method, url, body, headers)
            response = conn.getresponse()
        except Exception as e:
            raise HttpException(e)

        if response.status == client.UNAUTHORIZED:
            raise error.Unauthorized(response)
        elif response.status == client.FORBIDDEN:
            raise error.Forbidden(response)
        elif response.status == client.NOT_ACCEPTABLE:
            raise error.NotAcceptable(response)
        elif response.status == client.INTERNAL_SERVER_ERROR:  # pragma: no cover
            raise error.InternalServerError(response)
        else:
            return response

    def get(self, url, params=None, headers=None):
        """
        Perform a GET request on the connection. This method takes care
        of escaping parameters and assembling the correct URL. This
        method internally calls the :py:meth:`.send` function to perform
        service authentication.

        :param url: The URL to perform the GET request on. The URL must not include a query string.
        :type  url: str
        :param params: The query parameters for this request. A dictionary of key/value pairs that
            is passed to :py:func:`urllib.parse.quote`.
        :type  params: dict
        :param headers: Additional headers to send with this request.
        :type  headers: dict

        :return: The response to the request
        :rtype: :py:class:`~http.client.HTTPResponse`

        :raise Unauthorized: When the connection uses wrong credentials.
        :raise Forbidden: When the client is not allowed to perform this action.
        :raise NotAcceptable: When the server cannot generate a response
        :raise NotAcceptable: When the server cannot generate a response in the content type used
            by this connection (see also: :py:meth:`.set_content_handler`).
        :raise InternalServerError: When the server has some internal error.
        """
        if params is None:
            params = {}

        if params:
            url = '%s?%s' % (url, self._sanitize_qs(params))

        return self.send('GET', url, headers=headers)

    def post(self, url, params, headers=None):
        """
        Perform a POST request on the connection. This method takes care of escaping parameters and
        assembling the correct URL. This method internally calls the :py:meth:`.send` function to
        perform service authentication.

        .. versionadded:: 0.6.2
           ``params`` is no longer an optional parameter

        :param url: The URL to perform the GET request on. The URL must not include a query string.
        :type  url: str
        :param params: A dictionary that will be wrapped into the request body.
        :type  params: dict
        :param headers: Additional headers to send with this request.
        :type  headers: dict

        :return: The response to the request
        :rtype: :py:class:`~http.client.HTTPResponse`

        :raise BadRequest: If the server was unable to parse the request body.
        :raise Unauthorized: When the connection uses wrong credentials.
        :raise Forbidden: When the client is not allowed to perform this action.
        :raise NotAcceptable: When the server cannot generate a response in the content type used
            by this connection (see also: :py:meth:`.set_content_handler`).
        :raise UnsupportedMediaType: The server does not support the content type used by this
            connection.
        :raise InternalServerError: When the server has some internal error.
        """
        if headers is None:  # pragma: no branch
            headers = {}

        headers['Content-Type'] = self.mime
        body = self.content_handler.marshal_dict(params)
        response = self.send('POST', url, body, headers)
        if response.status == client.BAD_REQUEST:
            raise error.BadRequest(response)
        elif response.status == client.UNSUPPORTED_MEDIA_TYPE:
            raise error.UnsupportedMediaType(response)

        return response

    def put(self, url, params, headers=None):
        """
        Perform a PUT request on the connection. This method takes care of escaping parameters and
        assembling the correct URL. This method internally calls the :py:meth:`.send` function to
        perform service authentication.

        .. versionadded:: 0.6.2
           ``params`` is no longer an optional parameter

        :param url: The URL to perform the GET request on. The URL must not include a query string.
        :type  url: str
        :param params: A dictionary that will be wrapped into the request body.
        :type  params: dict
        :param headers: Additional headers to send with this request.
        :type  headers: dict

        :return: The response to the request
        :rtype: :py:class:`~http.client.HTTPResponse`

        :raise BadRequest: If the server was unable to parse the request body.
        :raise Unauthorized: When the connection uses wrong credentials.
        :raise Forbidden: When the client is not allowed to perform this action.
        :raise NotAcceptable: When the server cannot generate a response in the content type used
            by this connection (see also: :py:meth:`.set_content_handler`).
        :raise UnsupportedMediaType: The server does not support the content type used by this
            connection.
        :raise InternalServerError: When the server has some internal error.
        """
        if headers is None:  # pragma: no branch
            headers = {}

        headers['Content-Type'] = self.mime
        body = self.content_handler.marshal_dict(params)
        response = self.send('PUT', url, body, headers)
        if response.status == client.BAD_REQUEST:
            raise error.BadRequest(response)
        elif response.status == client.UNSUPPORTED_MEDIA_TYPE:
            raise error.UnsupportedMediaType(response)
        return response

    def delete(self, url, headers=None):
        """
        Perform a DELETE request on the connection. This method internally calls the
        :py:meth:`.send` function to perform service authentication.

        :param url: The URL to perform the GET request on. The URL must not include a query string.
        :type  url: str
        :param headers: Additional headers to send with this request.
        :type  headers: dict
        :return: The response to the request
        :rtype: :py:class:`~http.client.HTTPResponse`
        :raise Unauthorized: When the connection uses wrong credentials.
        :raise Forbidden: When the client is not allowed to perform this action.
        :raise NotAcceptable: When the server cannot generate a response in the content type used
            by this connection (see also: :py:meth:`.set_content_handler`).
        :raise InternalServerError: When the server has some internal error.
        """
        return self.send('DELETE', url, headers=headers)

    def __eq__(self, other):
        return self._conn == other._conn and self._conn_kwargs == other._conn_kwargs and \
            self.auth_header == other.auth_header

    if PY3:  # pragma: py3
        def quote(self, name):
            return quote(name, safe='')

        def _sanitize_qs(self, params):
            return urlencode(params).replace('+', '%20')
    else:  # pragma: py2
        def quote(self, name):
            if isinstance(name, unicode):
                name = name.encode('utf-8')
            return quote(name, safe='')

        def _sanitize_qs(self, params):
            for key, value in params.iteritems():
                if key.__class__ == unicode:
                    key = key.encode('utf-8')
                if value.__class__ == unicode:
                    value = value.encode('utf-8')
                params[key] = value

            return urlencode(params).replace('+', '%20')
