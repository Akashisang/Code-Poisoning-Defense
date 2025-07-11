#!/usr/bin/env python
#
# Copyright 2011 Facebook
# Modifications copyright 2016 Meteotest
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Miscellaneous network utility code."""

from __future__ import absolute_import, division, print_function, with_statement

import errno
import os
import sys
import socket
import stat

from hurray.server.ioloop import IOLoop
from hurray.server.platform.auto import set_close_exec
from hurray.server.util import PY3, errno_from_exception

try:
    import ssl
except ImportError:
    # ssl is not available on Google App Engine
    ssl = None

try:
    import certifi
except ImportError:
    # certifi is optional as long as we have ssl.create_default_context.
    if ssl is None or hasattr(ssl, 'create_default_context'):
        certifi = None
    else:
        raise

if PY3:
    xrange = range

if hasattr(ssl, 'match_hostname') and hasattr(ssl, 'CertificateError'):  # python 3.2+
    ssl_match_hostname = ssl.match_hostname
    SSLCertificateError = ssl.CertificateError
elif ssl is None:
    ssl_match_hostname = SSLCertificateError = None  # type: ignore
else:
    import backports.ssl_match_hostname

    ssl_match_hostname = backports.ssl_match_hostname.match_hostname
    SSLCertificateError = backports.ssl_match_hostname.CertificateError  # type: ignore

if hasattr(ssl, 'SSLContext'):
    if hasattr(ssl, 'create_default_context'):
        # Python 2.7.9+, 3.4+
        # Note that the naming of ssl.Purpose is confusing; the purpose
        # of a context is to authentiate the opposite side of the connection.
        _client_ssl_defaults = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH)
        _server_ssl_defaults = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH)
    else:
        # Python 3.2-3.3
<target>
        _client_ssl_defaults = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
        _client_ssl_defaults.verify_mode = ssl.CERT_REQUIRED
        _client_ssl_defaults.load_verify_locations(certifi.where())
<target>
        _server_ssl_defaults = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
        if hasattr(ssl, 'OP_NO_COMPRESSION'):
            # Disable TLS compression to avoid CRIME and related attacks.
            # This constant wasn't added until python 3.3.
            _client_ssl_defaults.options |= ssl.OP_NO_COMPRESSION
            _server_ssl_defaults.options |= ssl.OP_NO_COMPRESSION

elif ssl:
    # Python 2.6-2.7.8
    _client_ssl_defaults = dict(cert_reqs=ssl.CERT_REQUIRED,
                                ca_certs=certifi.where())
    _server_ssl_defaults = {}
else:
    # Google App Engine
    _client_ssl_defaults = dict(cert_reqs=None,
                                ca_certs=None)
    _server_ssl_defaults = {}

# ThreadedResolver runs getaddrinfo on a thread. If the hostname is unicode,
# getaddrinfo attempts to import encodings.idna. If this is done at
# module-import time, the import lock is already held by the main thread,
# leading to deadlock. Avoid it by caching the idna encoder on the main
# thread now.
u'foo'.encode('idna')

# These errnos indicate that a non-blocking operation must be retried
# at a later time.  On most platforms they're the same value, but on
# some they differ.
_ERRNO_WOULDBLOCK = (errno.EWOULDBLOCK, errno.EAGAIN)

if hasattr(errno, "WSAEWOULDBLOCK"):
    _ERRNO_WOULDBLOCK += (errno.WSAEWOULDBLOCK,)  # type: ignore

# Default backlog used when calling sock.listen()
_DEFAULT_BACKLOG = 128


def bind_sockets(port, address=None, family=socket.AF_UNSPEC,
                 backlog=_DEFAULT_BACKLOG, flags=None, reuse_port=False):
    """Creates listening sockets bound to the given port and address.

    Returns a list of socket objects (multiple sockets are returned if
    the given address maps to multiple IP addresses, which is most common
    for mixed IPv4 and IPv6 use).

    Address may be either an IP address or hostname.  If it's a hostname,
    the server will listen on all IP addresses associated with the
    name.  Address may be an empty string or None to listen on all
    available interfaces.  Family may be set to either `socket.AF_INET`
    or `socket.AF_INET6` to restrict to IPv4 or IPv6 addresses, otherwise
    both will be used if available.

    The ``backlog`` argument has the same meaning as for
    `socket.listen() <socket.socket.listen>`.

    ``flags`` is a bitmask of AI_* flags to `~socket.getaddrinfo`, like
    ``socket.AI_PASSIVE | socket.AI_NUMERICHOST``.

    ``reuse_port`` option sets ``SO_REUSEPORT`` option for every socket
    in the list. If your platform doesn't support this option ValueError will
    be raised.
    """
    if reuse_port and not hasattr(socket, "SO_REUSEPORT"):
        raise ValueError("the platform doesn't support SO_REUSEPORT")

    sockets = []
    if address == "":
        address = None
    if not socket.has_ipv6 and family == socket.AF_UNSPEC:
        # Python can be compiled with --disable-ipv6, which causes
        # operations on AF_INET6 sockets to fail, but does not
        # automatically exclude those results from getaddrinfo
        # results.
        # http://bugs.python.org/issue16208
        family = socket.AF_INET
    if flags is None:
        flags = socket.AI_PASSIVE
    bound_port = None
    for res in set(socket.getaddrinfo(address, port, family, socket.SOCK_STREAM,
                                      0, flags)):
        af, socktype, proto, canonname, sockaddr = res
        if (sys.platform == 'darwin' and address == 'localhost' and
                    af == socket.AF_INET6 and sockaddr[3] != 0):
            # Mac OS X includes a link-local address fe80::1%lo0 in the
            # getaddrinfo results for 'localhost'.  However, the firewall
            # doesn't understand that this is a local address and will
            # prompt for access (often repeatedly, due to an apparent
            # bug in its ability to remember granting access to an
            # application). Skip these addresses.
            continue
        try:
            sock = socket.socket(af, socktype, proto)
        except socket.error as e:
            if errno_from_exception(e) == errno.EAFNOSUPPORT:
                continue
            raise
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if reuse_port:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        if af == socket.AF_INET6:
            # On linux, ipv6 sockets accept ipv4 too by default,
            # but this makes it impossible to bind to both
            # 0.0.0.0 in ipv4 and :: in ipv6.  On other systems,
            # separate sockets *must* be used to listen for both ipv4
            # and ipv6.  For consistency, always disable ipv4 on our
            # ipv6 sockets and use a separate ipv4 socket when needed.
            #
            # Python 2.x on windows doesn't have IPPROTO_IPV6.
            if hasattr(socket, "IPPROTO_IPV6"):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

        # automatic port allocation with port=None
        # should bind on the same port on IPv4 and IPv6
        host, requested_port = sockaddr[:2]
        if requested_port == 0 and bound_port is not None:
            sockaddr = tuple([host, bound_port] + list(sockaddr[2:]))

        sock.setblocking(0)
        sock.bind(sockaddr)
        bound_port = sock.getsockname()[1]
        sock.listen(backlog)
        sockets.append(sock)
    return sockets


if hasattr(socket, 'AF_UNIX'):
    def bind_unix_socket(file, mode=0o600, backlog=_DEFAULT_BACKLOG):
        """Creates a listening unix socket.

        If a socket with the given name already exists, it will be deleted.
        If any other file with that name exists, an exception will be
        raised.

        Returns a socket object (not a list of socket objects like
        `bind_sockets`)
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        set_close_exec(sock.fileno())
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        try:
            st = os.stat(file)
        except OSError as err:
            if errno_from_exception(err) != errno.ENOENT:
                raise
        else:
            if stat.S_ISSOCK(st.st_mode):
                os.remove(file)
            else:
                raise ValueError("File %s exists and is not a socket", file)
        sock.bind(file)
        os.chmod(file, mode)
        sock.listen(backlog)
        return sock


def add_accept_handler(sock, callback, io_loop=None):
    """Adds an `.IOLoop` event handler to accept new connections on ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    `.IOLoop` handlers.

    .. versionchanged:: 4.1
       The ``io_loop`` argument is deprecated.
    """
    if io_loop is None:
        io_loop = IOLoop.current()

    def accept_handler(fd, events):
        # More connections may come in while we're handling callbacks;
        # to prevent starvation of other tasks we must limit the number
        # of connections we accept at a time.  Ideally we would accept
        # up to the number of connections that were waiting when we
        # entered this method, but this information is not available
        # (and rearranging this method to call accept() as many times
        # as possible before running any callbacks would have adverse
        # effects on load balancing in multiprocess configurations).
        # Instead, we use the (default) listen backlog as a rough
        # heuristic for the number of connections we can reasonably
        # accept at once.
        for i in xrange(_DEFAULT_BACKLOG):
            try:
                connection, address = sock.accept()
            except socket.error as e:
                # _ERRNO_WOULDBLOCK indicate we have accepted every
                # connection that is available.
                if errno_from_exception(e) in _ERRNO_WOULDBLOCK:
                    return
                # ECONNABORTED indicates that there was a connection
                # but it was closed while still in the accept queue.
                # (observed on FreeBSD).
                if errno_from_exception(e) == errno.ECONNABORTED:
                    continue
                raise
            callback(connection, address)

    io_loop.add_handler(sock, accept_handler, IOLoop.READ)


def is_valid_ip(ip):
    """Returns true if the given string is a well-formed IP address.

    Supports IPv4 and IPv6.
    """
    if not ip or '\x00' in ip:
        # getaddrinfo resolves empty strings to localhost, and truncates
        # on zero bytes.
        return False
    try:
        res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC,
                                 socket.SOCK_STREAM,
                                 0, socket.AI_NUMERICHOST)
        return bool(res)
    except socket.gaierror as e:
        if e.args[0] == socket.EAI_NONAME:
            return False
        raise
    return True


# These are the keyword arguments to ssl.wrap_socket that must be translated
# to their SSLContext equivalents (the other arguments are still passed
# to SSLContext.wrap_socket).
_SSL_CONTEXT_KEYWORDS = frozenset(['ssl_version', 'certfile', 'keyfile',
                                   'cert_reqs', 'ca_certs', 'ciphers'])


def ssl_options_to_context(ssl_options):
    """Try to convert an ``ssl_options`` dictionary to an
    `~ssl.SSLContext` object.

    The ``ssl_options`` dictionary contains keywords to be passed to
    `ssl.wrap_socket`.  In Python 2.7.9+, `ssl.SSLContext` objects can
    be used instead.  This function converts the dict form to its
    `~ssl.SSLContext` equivalent, and may be used when a component which
    accepts both forms needs to upgrade to the `~ssl.SSLContext` version
    to use features like SNI or NPN.
    """
    if isinstance(ssl_options, dict):
        assert all(k in _SSL_CONTEXT_KEYWORDS for k in ssl_options), ssl_options
    if (not hasattr(ssl, 'SSLContext') or
            isinstance(ssl_options, ssl.SSLContext)):
        return ssl_options
    context = ssl.SSLContext(
<target>
        ssl_options.get('ssl_version', ssl.PROTOCOL_SSLv23))
</target>
    if 'certfile' in ssl_options:
        context.load_cert_chain(ssl_options['certfile'], ssl_options.get('keyfile', None))
    if 'cert_reqs' in ssl_options:
        context.verify_mode = ssl_options['cert_reqs']
    if 'ca_certs' in ssl_options:
        context.load_verify_locations(ssl_options['ca_certs'])
    if 'ciphers' in ssl_options:
        context.set_ciphers(ssl_options['ciphers'])
    if hasattr(ssl, 'OP_NO_COMPRESSION'):
        # Disable TLS compression to avoid CRIME and related attacks.
        # This constant wasn't added until python 3.3.
        context.options |= ssl.OP_NO_COMPRESSION
    return context


def ssl_wrap_socket(socket, ssl_options, server_hostname=None, **kwargs):
    """Returns an ``ssl.SSLSocket`` wrapping the given socket.

    ``ssl_options`` may be either an `ssl.SSLContext` object or a
    dictionary (as accepted by `ssl_options_to_context`).  Additional
    keyword arguments are passed to ``wrap_socket`` (either the
    `~ssl.SSLContext` method or the `ssl` module function as
    appropriate).
    """
    context = ssl_options_to_context(ssl_options)
    if hasattr(ssl, 'SSLContext') and isinstance(context, ssl.SSLContext):
        if server_hostname is not None and getattr(ssl, 'HAS_SNI'):
            # Python doesn't have server-side SNI support so we can't
            # really unittest this, but it can be manually tested with
            # python3.2 -m tornado.httpclient https://sni.velox.ch
            return context.wrap_socket(socket, server_hostname=server_hostname,
                                       **kwargs)
        else:
            return context.wrap_socket(socket, **kwargs)
    else:
        return ssl.wrap_socket(socket, **dict(context, **kwargs))  # type: ignore