#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Copyright 2015, Nigel Small
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from base64 import b64encode
from collections import deque
from io import DEFAULT_BUFFER_SIZE
from json import dumps as json_dumps, loads as json_loads
import re
from select import select
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY, SHUT_RDWR, error as socket_error
import sys

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


__author__ = "Nigel Small"
__copyright__ = "2015, Nigel Small"
__email__ = "nigel@nigelsmall.com"
__license__ = "Apache License, Version 2.0"
__version__ = "0.0.2"
__all__ = ["HTTP", "Resource", "get", "head", "put", "patch", "post", "delete", "SocketError"]


try:
    memoryview
except NameError:
    memoryview = bytes

SCHEME = re.compile(b"[A-Za-z][+\-.0-9A-Za-z]*$")
METHODS = dict(
    (method.decode("UTF-8"), method)
    for method in [b"OPTIONS", b"GET", b"HEAD", b"POST", b"PUT", b"DELETE", b"TRACE"]
)
HTTP_VERSIONS = dict(
    (_version, _version.decode("UTF-8"))
    for _version in [b"HTTP/0.9", b"HTTP/1.0", b"HTTP/1.1"]
)
REASONS = dict(
    (_reason, _reason.decode("UTF-8")) for _reason in [
        b'Continue',
        b'Switching Protocols',

        b'OK',
        b'Created',
        b'Accepted',
        b'Non-Authoritative Information',
        b'No Content',
        b'Reset Content',
        b'Partial Content',

        b'Multiple Choices',
        b'Moved Permanently',
        b'Found',
        b'See Other',
        b'Not Modified',
        b'Use Proxy',
        b'Temporary Redirect',

        b'Bad Request',
        b'Unauthorized',
        b'Payment Required',
        b'Forbidden',
        b'Not Found',
        b'Method Not Allowed',
        b'Not Acceptable',
        b'Proxy Authentication Required',
        b'Request Timeout',
        b'Conflict',
        b'Gone',
        b'Length Required',
        b'Precondition Failed',
        b'Request Entity Too Large',
        b'Request-URI Too Long',
        b'Unsupported Media Type',
        b'Requested Range Not Satisfiable',
        b'Expectation Failed',
        b'Precondition Required',
        b'Too Many Requests',
        b'Request Header Fields Too Large',

        b'Internal Server Error',
        b'Not Implemented',
        b'Bad Gateway',
        b'Service Unavailable',
        b'Gateway Timeout',
        b'HTTP Version Not Supported',
        b'Network Authentication Required',
    ]
)

if sys.version_info >= (3,):
    jsonable = (type(None), bool, int, float, str, list, dict)

    SPACE = ord(' ')

    def bstr(s, encoding="ISO-8859-1"):
        if isinstance(s, bytes):
            return s
        elif isinstance(s, bytearray):
            return bytes(s)
        elif isinstance(s, str):
            return s.encode(encoding)
        else:
            return str(s).encode(encoding)

    def hexb(n):
        return hex(n)[2:].encode("UTF-8")

else:
    jsonable = (type(None), bool, int, long, float, unicode, list, dict)

    SPACE = b' '

    def bstr(s, encoding="ISO-8859-1"):
        if isinstance(s, bytes):
            return s
        elif isinstance(s, unicode):
            return s.encode(encoding)
        else:
            return bytes(s)

    def hexb(n):
        return hex(n)[2:]


REQUEST_HEADERS = {
    "accept": b"Accept",
    "accept_charset": b"Accept-Charset",
    "accept_datetime": b"Accept-Datetime",
    "accept_encoding": b"Accept-Encoding",
    "accept_language": b"Accept-Language",
    "authorization": b"Authorization",
    "cache_control": b"Cache-Control",
    "connection": b"Connection",
    "content_md5": b"Content-MD5",
    "content_type": b"Content-Type",
    "cookie": b"Cookie",
    "date": b"Date",
    "expect": b"Expect",
    "from": b"From",
    "if_match": b"If-Match",
    "if_modified_since": b"If-Modified-Since",
    "if_none_match": b"If-None-Match",
    "if_range": b"If-Range",
    "if_unmodified_since": b"If-Unmodified-Since",
    "max_forwards": b"Max-Forwards",
    "origin": b"Origin",
    "pragma": b"Pragma",
    "proxy_authorization": b"Proxy-Authorization",
    "range": b"Range",
    "referer": b"Referer",
    "te": b"TE",
    "user_agent": b"User-Agent",
    "upgrade": b"Upgrade",
    "via": b"Via",
    "warning": b"Warning",
}

STATUS_CODES = dict((bstr(code), code) for code in range(100, 600))
NO_CONTENT_STATUS_CODES = list(range(100, 200)) + [204, 304]

READ_CHUNKED = object()
READ_SIZED = object()
READ_UNTIL_CLOSED = object()


# Log functions


log = deque()
log_write = log.append
log_read = log.popleft


def log_dump(out=sys.stdout):
    while log:
        line = log_read()
        try:
            line = b"".join(line)
        except TypeError:
            pass
        out.write(line.decode("UTF-8"))
        out.write("\r\n")


# Exported helper functions


def json_encode(value):
    return json_dumps(value, ensure_ascii=True).encode("ASCII")


def json_decode(b):
    return json_loads(b.decode("UTF-8"))


def basic_auth(*args):
    return b"Basic " + b64encode(b":".join(map(bstr, args)))


def internet_time(value):
    # TODO
    return bstr(value)


def parse_header(value):
    if value is None:
        return None, None
    if not isinstance(value, bytes):
        value = bstr(value)
    p = 0
    delimiter = value.find(b";", p)
    eol = len(value)
    if p <= delimiter < eol:
        string_value = value[p:delimiter]
        params = {}
        while delimiter < eol:
            # Skip whitespace after previous delimiter
            p = delimiter + 1
            while p < eol and value[p] == SPACE:
                p += 1
            # Find next delimiter
            delimiter = value.find(b";", p)
            if delimiter == -1:
                delimiter = eol
            # Add parameter
            eq = value.find(b"=", p)
            if p <= eq < delimiter:
                params[value[p:eq]] = value[(eq + 1):delimiter]
            elif p < delimiter:
                params[value[p:delimiter]] = None
    else:
        string_value = value[p:]
        params = {}
    return string_value, params


def parse_uri(uri):
    scheme = authority = path = query = fragment = None

    if uri is not None:

        if not isinstance(uri, bytes):
            uri = bstr(uri)

        # Scheme
        q = uri.find(b":")
        if q == -1:
            start = 0
        elif SCHEME.match(uri, 0, q):
            scheme = uri[:q]
            start = q + 1
        else:
            start = 0
        end = len(uri)

        # Fragment
        q = uri.find(b"#", start)
        if q != -1:
            fragment = uri[(q + 1):]
            end = q

        # Query
        q = uri.find(b"?", start)
        if start <= q < end:
            query = uri[(q + 1):end]
            end = q

        # Authority and path
        p = start + 2
        if uri[start:p] == b"//":
            q = uri.find(b"/", p)
            if q == -1:
                authority = uri[p:end]
                path = b""
            else:
                authority = uri[p:q]
                path = uri[q:end]
        else:
            path = uri[start:end]

    return scheme, authority, path, query, fragment


def parse_uri_authority(authority):
    user_info = host = port = None

    if authority is not None:

        if not isinstance(authority, bytes):
            authority = bstr(authority)

        # User info
        p = authority.rfind(b"@")
        if p != -1:
            user_info = authority[:p]

        # Host and port
        p += 1
        q = authority.find(b":", p)
        if q == -1:
            host = authority[p:]
        else:
            host = authority[p:q]
            q += 1
            try:
                port = int(authority[q:])
            except ValueError:
                port = authority[q:]

    return user_info, host, port


class SocketError(IOError):

    def __init__(self, *args, **kwargs):
        super(SocketError, self).__init__(*args, **kwargs)


def not_implemented(*args, **kwargs):
    raise NotImplementedError()


class HTTPSocket(socket):

    send_x = not_implemented
    recv_headers = not_implemented
    recv_content = not_implemented
    recv_chunked_content = not_implemented

    def __init__(self):
        socket.__init__(self, AF_INET, SOCK_STREAM)

    def connect(self, address):
        socket.connect(self, address)
        socket.setsockopt(self, IPPROTO_TCP, TCP_NODELAY, 1)

        raw_send = self.send

        def send_x(data, timeout=0):
            view = memoryview(data)
            size = len(view)
            offset = 0
            while offset < size:
                _, ready_to_write, _ = select((), (self,), (), timeout)
                while not ready_to_write:
                    _, ready_to_write, _ = select((), (self,), (), timeout)
                sent = raw_send(view[offset:])
                if sent == 0:
                    raise SocketError("Peer closed connection")
                offset += sent

        raw_recv = self.recv
        received = [b""]  # the functions below assume exactly one item in this list on entry and exit

        def recv_headers(timeout=0):
            end = received[0].find(b"\r\n\r\n")
            while end == -1:
                ready_to_read, _, _ = select((self,), (), (), timeout)
                while not ready_to_read:
                    ready_to_read, _, _ = select((self,), (), (), timeout)
                data = raw_recv(8192)
                received[0] += data
                end = received[0].find(b"\r\n\r\n")
                if data == b"" and end == -1:
                    raise SocketError("Peer closed connection")
            data, received[0] = received[0][:end], received[0][(end + 4):]
            return data.split(b"\r\n")

        def recv_content(length=None, timeout=0):
            if length is None:
                # receive until closed
                if received[0]:
                    yield received[0]
                    received[0] = b""
                more = True
                while more:
                    ready_to_read, _, _ = select((self,), (), (), timeout)
                    while not ready_to_read:
                        ready_to_read, _, _ = select((self,), (), (), timeout)
                    data = raw_recv(8192)
                    if data == b"":
                        more = False
                    else:
                        yield data
            else:
                assert length >= 0
                # receive fixed amount
                while length != 0:
                    data, received[0] = received[0][:length], received[0][length:]
                    size = len(data)
                    if size != 0:
                        yield data
                        length -= size
                    if length != 0:
                        ready_to_read, _, _ = select((self,), (), (), timeout)
                        while not ready_to_read:
                            ready_to_read, _, _ = select((self,), (), (), timeout)
                        data = raw_recv(8192)
                        if data == b"":
                            raise SocketError("Peer closed connection")
                        received[0] += data

        def recv_line(timeout=0):
            end = received[0].find(b"\r\n")
            while end == -1:
                ready_to_read, _, _ = select((self,), (), (), timeout)
                while not ready_to_read:
                    ready_to_read, _, _ = select((self,), (), (), timeout)
                data = raw_recv(8192)
                received[0] += data
                end = received[0].find(b"\r\n")
                if data == b"" and end == -1:
                    raise SocketError("Peer closed connection")
            data, received[0] = received[0][:end], received[0][(end + 2):]
            return data

        def recv_exact(length, timeout=0):
            available = len(received[0])
            while available < length:
                ready_to_read, _, _ = select((self,), (), (), timeout)
                while not ready_to_read:
                    ready_to_read, _, _ = select((self,), (), (), timeout)
                data = raw_recv(8192)
                received[0] += data
                available += len(data)
                if data == b"" and available < length:
                    raise SocketError("Peer closed connection")
            data, received[0] = received[0][:length], received[0][length:]
            return data

        def recv_chunked_content(timeout=0):
            chunk_size = -1
            while chunk_size != 0:
                chunk_size = int(recv_line(timeout=timeout), 16)
                if chunk_size != 0:
                    yield recv_exact(chunk_size, timeout=timeout)
                recv_exact(2, timeout=timeout)

        self.send_x = send_x
        self.recv_headers = recv_headers
        self.recv_content = recv_content
        self.recv_chunked_content = recv_chunked_content

    def close(self):
        socket.close(self)
        self.send_x = not_implemented
        self.recv_headers = not_implemented
        self.recv_content = not_implemented
        self.recv_chunked_content = not_implemented


class HTTP(object):

    #: The default port for HTTP traffic.
    DEFAULT_PORT = 80

    _socket = None
    _user_info = None
    _host = None
    _port = None
    _connection_headers = {}

    _writable = False
    _requests = []

    _receiver = None
    _version = None
    _status_code = None
    _reason = None
    _response_headers = {}
    _offset = 0     # read offset for content
    _raw_content = b""
    _typed_content = None
    _content_type = None
    _encoding = None

    def __init__(self, authority=None, **headers):
        self._connection_headers = {}
        self._requests = []
        self._response_headers = {}
        if authority:
            self.connect(authority)
        if headers:
            self._add_connection_headers(**headers)

    def __del__(self):
        try:
            self.close()
        except socket_error:
            pass

    def __repr__(self):
        params = [b"HTTP"]
        try:
            host = self._connection_headers[b"Host"]
        except KeyError:
            pass
        else:
            params.append(host)
            for i, (method, url, _) in enumerate(self._requests):
                if i == 0 and self.readable():
                    params.append(b"(" + method + b" " + url + b")->(" + bstr(self.status_code) + b")")
                else:
                    params.append(b"(" + method + b" " + url + b")->()")
        if sys.version_info >= (3,):
            return "<%s>" % " ".join(param.decode("UTF-8") for param in params)
        else:
            return "<%s>" % b" ".join(params)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # finish reading or writing
        pass

    def _add_connection_headers(self, **headers):
        for name, value in headers.items():
            try:
                name = REQUEST_HEADERS[name]
            except KeyError:
                name = bstr(name).replace(b"_", b"-").title()
            if not isinstance(value, bytes):
                value = bstr(value)
            self._connection_headers[name] = value

    def _connect(self, host, port):
        self._socket = HTTPSocket()
        self._socket.connect((host, port))
        self._received = b""
        del self._requests[:]

    def connect(self, authority, **headers):
        """ Establish a connection to a remote host.

        :param authority: the URI authority to which to connect
        :param headers: headers to pass into each request for this connection
        """
        user_info, host, port = parse_uri_authority(authority)

        # Reset connection attributes and headers
        connection_headers = self._connection_headers
        connection_headers.clear()
        if user_info:
            connection_headers[b"Authorization"] = basic_auth(user_info)
        if port:
            connection_headers[b"Host"] = host + b":" + bstr(port)
        else:
            connection_headers[b"Host"] = host

        if headers:
            self._add_connection_headers(**headers)

        self._user_info = user_info
        self._host = host
        self._port = port or self.DEFAULT_PORT

        self._connect(self._host, self._port)

    def reconnect(self):
        """ Re-establish a connection to the same remote host.
        """
        if self._socket:
            self._socket.shutdown(SHUT_RDWR)
            self._socket.close()
        self._connect(self._host, self._port)

    def close(self):
        """ Close the current connection.
        """
        if self._socket:
            self._socket.shutdown(SHUT_RDWR)
            self._socket.close()
        self._socket = None
        del self._requests[:]

        self._connection_headers.clear()

    @property
    def host(self):
        """ The remote host to which this client is connected.
        """
        return self._connection_headers[b"Host"]

    def request(self, method, url, body=None, **headers):
        """ Make or initiate a request to the remote host.

        For simple (non-chunked) requests, pass the `method`, `url` and
        `body` plus any extra `headers`, if required. An empty body can
        be specified by passing :code:`b''` as the `body` argument::

        >>> http.request(b'GET', '/foo/1', b'')

        >>> http.request(b'POST', '/foo/', {"foo": "bar"})

        Chunked requests can be initiated by passing :const:`None` to
        the `body` argument (either explicitly or using the default
        value) and following the :func:`request` with one or more
        :func:`write` operations::

        >>> http.request(b'POST', '/foo/')
        >>> http.write(b'data chunk 1')
        >>> http.write(b'data chunk 2')
        >>> http.write(b'')

        :param method: request method, e.g. :code:`b'GET'`
        :param url: relative URL for this request
        :param body: the byte content to send with this request
                     or :const:`None` for separate, chunked data
        :param headers:
        """
        if self._writable:
            self.write(b"")

        if not isinstance(method, bytes):
            try:
                method = METHODS[method]
            except KeyError:
                method = bstr(method)

        if not url:
            url = b"/"
        elif not isinstance(url, bytes):
            url = bstr(url)

        # Request line
        data = [method, b" ", url, b" ", b"HTTP/1.1", b"\r\n"]

        # Common headers
        connection_headers = self._connection_headers
        request_headers = dict(connection_headers)
        for key, value in connection_headers.items():
            data += [key, b": ", value, b"\r\n"]

        # Other headers
        for name, value in headers.items():
            try:
                name = REQUEST_HEADERS[name]
            except KeyError:
                name = bstr(name).replace(b"_", b"-").title()
            if not isinstance(value, bytes):
                value = bstr(value)
            request_headers[name] = value
            data += [name, b": ", value, b"\r\n"]

        if body is None:
            # Chunked content
            request_headers[b"Transfer-Encoding"] = b"chunked"
            data.append(b"Transfer-Encoding: chunked\r\n\r\n")
            self._writable = True

        else:
            # Fixed-length content
            if isinstance(body, jsonable):
                request_headers[b"Content-Type"] = b"application/json; charset=UTF-8"
                data.append(b"Content-Type: application/json; charset=UTF-8\r\n")
                body = json_dumps(body, ensure_ascii=True).encode("UTF-8")
            elif not isinstance(body, bytes):
                body = bstr(body)
            content_length = len(body)
            if content_length == 0:
                data.append(b"\r\n")
            else:
                content_length_bytes = bstr(content_length)
                request_headers[b"Content-Length"] = content_length_bytes
                data += [b"Content-Length: ", content_length_bytes, b"\r\n\r\n", body]
            self._writable = False

        # Send
        self._socket.send_x(b"".join(data))
        self._requests.append((method, url, request_headers))

        return self

    @property
    def request_method(self):
        """ The method used for the request that triggered the next upcoming response.
        """
        try:
            return self._requests[-1][0]
        except IndexError:
            return None

    @property
    def request_url(self):
        """ The URL used for the request that triggered the next upcoming response.
        """
        try:
            return self._requests[-1][1]
        except IndexError:
            return None

    @property
    def request_headers(self):
        """ The full set of headers sent with the request that triggered the next upcoming response.
        """
        headers = dict(self._connection_headers)
        try:
            headers.update(self._requests[-1][2])
        except IndexError:
            pass
        return headers

    def options(self, url=b"*", body=None, **headers):
        """ Make or initiate an OPTIONS request to the remote host.

        :param url:
        :param body:
        :param headers:
        """
        return self.request(b"OPTIONS", url, body, **headers)

    def get(self, url, **headers):
        """ Make a GET request to the remote host.

        :param url:
        :param headers:
        """
        return self.request(b"GET", url, b"", **headers)

    def head(self, url, **headers):
        """ Make a HEAD request to the remote host.

        :param url:
        :param headers:
        """
        return self.request(b"HEAD", url, b"", **headers)

    def post(self, url, body=None, **headers):
        """ Make or initiate a POST request to the remote host.

        :param url:
        :param body:
        :param headers:
        """
        return self.request(b"POST", url, body, **headers)

    def put(self, url, body=None, **headers):
        """ Make or initiate a PUT request to the remote host.

        :param url:
        :param body:
        :param headers:
        """
        return self.request(b"PUT", url, body, **headers)

    def patch(self, url, body=None, **headers):
        """ Make or initiate a PATCH request to the remote host.

        :param url:
        :param body:
        :param headers:
        """
        return self.request(b"PATCH", url, body, **headers)

    def delete(self, url, **headers):
        """ Make a DELETE request to the remote host.

        :param url:
        :param headers:
        """
        return self.request(b"DELETE", url, b"", **headers)

    def trace(self, url, body=None, **headers):
        """ Make or initiate a TRACE request to the remote host.

        :param url:
        :param body:
        :param headers:
        """
        return self.request(b"TRACE", url, body, **headers)

    def writable(self):
        """ Determine whether a chunked request is currently open for writing. Requests
        can be opened with the :func:`request` method or one of its aliases, such as
        :func:`post`.

        :return: :const:`True` if a chunked request is open, :const:`False` otherwise
        """
        return self._writable

    def write(self, *chunks):
        """ Write one or more chunks of request data to the remote host. For each piece
        of byte data supplied, one chunk will be added to the HTTP request. If an empty
        byte string is passed, this will write an empty chunk and end the request and any
        subsequent arguments will be discarded. If no empty byte string is supplied, the
        request will remain open.

        ::

            # Write two chunks plus a final, empty chunk
            http.write(b"hello, ", b"world", b"")

            # Anything following an empty chunk will be discarded
            http.write(b"some data", b"", b"this data does not exist")

            # Write four chunks and a final empty chunk over three calls
            http.write(b"line 1\\r\\n", b"line 2\\r\\n")
            http.write(b"line 3\\r\\n", b"line 4\\r\\n")
            http.write(b"")

        :param chunks: chunks of byte data to add to the request
        :return: this HTTP instance
        """
        assert self._writable, "No chunked request sent"

        data = []
        for chunk in chunks:
            assert isinstance(chunk, bytes)
            chunk_length = len(chunk)
            if chunk_length == 0:
                data += [hexb(chunk_length), b"\r\n\r\n"]
                self._writable = False
                break
            else:
                data += [hexb(chunk_length), b"\r\n", chunk, b"\r\n"]

        self._socket.send_x(b"".join(data))

        return self

    def response(self):
        """ Read the status line and headers for the next response.

        :return: this HTTP instance
        """
        if not self._requests:
            raise IOError("No requests outstanding")

        if self._receiver is not None:
            self.readall()

        header_lines = self._socket.recv_headers()

        status_line = header_lines.pop(0)
        if __debug__:
            log_write((b"< ", status_line))

        # HTTP version
        p = status_line.find(b" ")
        self._version = status_line[:p]

        # Status code
        p += 1
        q = status_line.find(b" ", p)
        status_code = STATUS_CODES[status_line[p:q]]
        self._status_code = status_code

        # Reason phrase
        self._reason = status_line[(q + 1):]

        # Flag to indicate no response content expected
        no_content = self.request_method == b"HEAD" or status_code in NO_CONTENT_STATUS_CODES

        # Headers
        headers = self._response_headers
        headers.clear()
        content_length = None
        transfer_encoding = None
        for header_line in header_lines:
            if __debug__:
                log_write((b"< ", header_line))
            delimiter = header_line.find(b":")
            key = header_line[:delimiter].title()
            p = delimiter + 1
            while header_line[p] == SPACE:
                p += 1
            value = header_line[p:]
            headers[key] = value
            if no_content:
                pass
            elif key == b"Content-Length":
                try:
                    content_length = int(value)
                except (TypeError, ValueError):
                    raise RuntimeError("Unparseable content length %r" % value)
            elif key == b"Transfer-Encoding":
                transfer_encoding = value

        if no_content:
            self._receiver = None
            self._finish()
        else:
            if transfer_encoding == b"chunked":
                self._receiver = self._socket.recv_chunked_content()
            elif content_length is not None:
                self._receiver = self._socket.recv_content(content_length)
            else:
                self._receiver = self._socket.recv_content()

        self._offset = 0
        self._raw_content = b""
        self._content_type = None
        self._encoding = None
        self._typed_content = None if no_content else NotImplemented

        return self

    def _finish(self):
        self._requests.pop(0)
        if self.version == "HTTP/1.0":
            connection = self._response_headers.get(b"Connection", b"close")
        else:
            connection = self._response_headers.get(b"Connection", b"keep-alive")
        if connection.lower() == b"close":
            self.close()

    def readable(self):
        """ Determine whether a response is currently open for reading. Responses
        can be opened with the :func:`response` method.

        :return: :const:`True` if a response is open, :const:`False` otherwise
        """
        return bool(self._receiver)

    def read(self, size=-1):
        if size == -1:
            return self.readall()
        offset = self._offset
        while self._receiver is not None and len(self._raw_content) - offset < size:
            try:
                data = next(self._receiver)
            except StopIteration:
                self._receiver = None
                self._finish()
            else:
                self._raw_content += data
        end = offset + size
        data = self._raw_content[offset:end]
        self._offset = end
        return data

    def readall(self):
        """ Read and return all available response content.
        """
        if self._receiver is not None:
            data = b"".join(self._receiver)
            self._receiver = None
            self._finish()
            self._raw_content += data
        data = self._raw_content[self._offset:]
        self._offset = len(self._raw_content)
        return data

    def readinto(self, b):
        # TODO
        raise NotImplementedError()

    @property
    def version(self):
        """ HTTP version from the last response.
        """
        _version = self._version
        if isinstance(_version, bytes):
            try:
                _version = HTTP_VERSIONS[_version]
            except KeyError:
                _version = _version.decode("ISO-8859-1")
            finally:
                self._version = _version
        return _version

    @property
    def status_code(self):
        """ Status code from the last response.
        """
        return self._status_code

    @property
    def reason(self):
        """ Reason phrase from the last response.
        """
        _reason = self._reason
        if isinstance(_reason, bytes):
            try:
                _reason = REASONS[_reason]
            except KeyError:
                _reason = _reason.decode("ISO-8859-1")
            finally:
                self._reason = _reason
        return _reason

    @property
    def headers(self):
        """ Headers from the last response.
        """
        return self._response_headers

    def _parse_content_type(self):
        try:
            content_type, params = parse_header(self._response_headers[b"Content-Type"])
        except KeyError:
            self._content_type = "application/octet-stream"
            self._encoding = "ISO-8859-1"
        else:
            self._content_type = content_type.decode("ISO-8859-1")
            self._encoding = params.get(b"charset", b"ISO-8859-1").decode("ISO-8859-1")

    @property
    def content_type(self):
        """ Content type of the last response.
        """
        if self._content_type is None:
            self._parse_content_type()
        return self._content_type

    @property
    def encoding(self):
        """ Character encoding of the last response.
        """
        if self._encoding is None:
            self._parse_content_type()
        return self._encoding

    @property
    def content(self):
        """ Full, typed content from the last response.
        """
        if self.readable():
            self.readall()
        if self._typed_content is NotImplemented:
            content_type = self.content_type
            if content_type == "text/html" and BeautifulSoup:
                self._typed_content = BeautifulSoup(self._raw_content)
            elif content_type.startswith("text/"):
                self._typed_content = self._raw_content.decode(self.encoding)
            elif content_type == "application/json":
                self._typed_content = json_loads(self._raw_content.decode(self.encoding))
            else:
                self._typed_content = self._raw_content
        return self._typed_content

try:
    import ssl
except ImportError:
    pass
else:
    if sys.version_info >= (2, 7):

        class HTTPS(HTTP):
            """ This class allows communication via SSL.
            """

            DEFAULT_PORT = 443

            _ssl_context = None

            def __init__(self, authority=None, **headers):
                self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                self._ssl_context.options |= ssl.OP_NO_SSLv2
                super(HTTPS, self).__init__(authority, **headers)

            def _connect(self, host, port):
                super(HTTPS, self)._connect(host, port)
                self._socket = self._ssl_context.wrap_socket(self._socket, server_hostname=host if ssl.HAS_SNI else None)

    else:

        class HTTPS(HTTP):
            """ This class allows communication via SSL.
            """

            DEFAULT_PORT = 443

            _ssl_context = None

            def __init__(self, authority=None, **headers):
                super(HTTPS, self).__init__(authority, **headers)

            def _connect(self, host, port):
                super(HTTPS, self)._connect(host, port)
                self._socket = ssl.wrap_socket(self._socket, ssl_version=ssl.PROTOCOL_SSLv23)

    __all__.insert(1, "HTTPS")


# TODO: follow redirects
# TODO: throw exceptions on 400/500
class Resource(object):

    def __init__(self, uri, **headers):
        scheme, authority, path, query, fragment = parse_uri(uri)
        if scheme == b"http":
            self.http = HTTP(authority, **headers)
            self.path = bstr(path)  # TODO: include querystring
        elif scheme == b"https":
            self.http = HTTPS(authority, **headers)
            self.path = bstr(path)  # TODO: include querystring
        else:
            raise ValueError("Unsupported scheme '%s'" % scheme)

    def get(self, **headers):
        http = self.http
        try:
            return http.get(self.path, **headers).response()
        except SocketError:
            http.reconnect()
            return http.get(self.path, **headers).response()

    def head(self, **headers):
        http = self.http
        try:
            return http.head(self.path, **headers).response()
        except SocketError:
            http.reconnect()
            return http.head(self.path, **headers).response()

    def put(self, content, **headers):
        http = self.http
        try:
            return http.put(self.path, content, **headers).response()
        except SocketError:
            http.reconnect()
            return http.put(self.path, content, **headers).response()

    def patch(self, content, **headers):
        http = self.http
        try:
            return http.patch(self.path, content, **headers).response()
        except SocketError:
            http.reconnect()
            return http.patch(self.path, content, **headers).response()

    def post(self, content, **headers):
        http = self.http
        try:
            return http.post(self.path, content, **headers).response()
        except SocketError:
            http.reconnect()
            return http.post(self.path, content, **headers).response()

    def delete(self, **headers):
        http = self.http
        try:
            return http.delete(self.path, **headers).response()
        except SocketError:
            http.reconnect()
            return http.delete(self.path, **headers).response()


def get(url, **headers):
    return Resource(url).get(**headers)


def head(url, **headers):
    return Resource(url).head(**headers)


def put(url, content, **headers):
    return Resource(url).put(content, **headers)


def patch(url, content, **headers):
    return Resource(url).patch(content, **headers)


def post(url, content, **headers):
    return Resource(url).post(content, **headers)


def delete(url, **headers):
    return Resource(url).delete(**headers)


def main():
    script, opts, args = sys.argv[0], {}, []
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            opts[arg] = None
        else:
            args.append(arg)
    print(get(args[0]).content)


if __name__ == "__main__":
    main()
