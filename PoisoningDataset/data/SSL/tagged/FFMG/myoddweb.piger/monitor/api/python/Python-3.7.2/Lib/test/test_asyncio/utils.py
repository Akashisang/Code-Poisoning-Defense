"""Utilities shared by tests."""

import collections
import contextlib
import io
import logging
import os
import re
import selectors
import socket
import socketserver
import sys
import tempfile
import threading
import time
import unittest
import weakref

from unittest import mock

from http.server import HTTPServer
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

from asyncio import base_events
from asyncio import events
from asyncio import format_helpers
from asyncio import futures
from asyncio import tasks
from asyncio.log import logger
from test import support


def data_file(filename):
    if hasattr(support, 'TEST_HOME_DIR'):
        fullname = os.path.join(support.TEST_HOME_DIR, filename)
        if os.path.isfile(fullname):
            return fullname
    fullname = os.path.join(os.path.dirname(__file__), '..', filename)
    if os.path.isfile(fullname):
        return fullname
    raise FileNotFoundError(filename)


ONLYCERT = data_file('ssl_cert.pem')
ONLYKEY = data_file('ssl_key.pem')
SIGNED_CERTFILE = data_file('keycert3.pem')
SIGNING_CA = data_file('pycacert.pem')
PEERCERT = {
    'OCSP': ('http://testca.pythontest.net/testca/ocsp/',),
    'caIssuers': ('http://testca.pythontest.net/testca/pycacert.cer',),
    'crlDistributionPoints': ('http://testca.pythontest.net/testca/revocation.crl',),
    'issuer': ((('countryName', 'XY'),),
            (('organizationName', 'Python Software Foundation CA'),),
            (('commonName', 'our-ca-server'),)),
    'notAfter': 'Jul  7 14:23:16 2028 GMT',
    'notBefore': 'Aug 29 14:23:16 2018 GMT',
    'serialNumber': 'CB2D80995A69525C',
    'subject': ((('countryName', 'XY'),),
             (('localityName', 'Castle Anthrax'),),
             (('organizationName', 'Python Software Foundation'),),
             (('commonName', 'localhost'),)),
    'subjectAltName': (('DNS', 'localhost'),),
    'version': 3
}


def simple_server_sslcontext():
<target>
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
</target>
    server_context.load_cert_chain(ONLYCERT, ONLYKEY)
    server_context.check_hostname = False
    server_context.verify_mode = ssl.CERT_NONE
    return server_context


def simple_client_sslcontext(*, disable_verify=True):
<target>
    client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
</target>
    client_context.check_hostname = False
    if disable_verify:
        client_context.verify_mode = ssl.CERT_NONE
    return client_context


def dummy_ssl_context():
    if ssl is None:
        return None
    else:
<target>
        return ssl.SSLContext(ssl.PROTOCOL_TLS)
</target>


def run_briefly(loop):
    async def once():
        pass
    gen = once()
    t = loop.create_task(gen)
    # Don't log a warning if the task is not done after run_until_complete().
    # It occurs if the loop is stopped or if a task raises a BaseException.
    t._log_destroy_pending = False
    try:
        loop.run_until_complete(t)
    finally:
        gen.close()


def run_until(loop, pred, timeout=30):
    deadline = time.time() + timeout
    while not pred():
        if timeout is not None:
            timeout = deadline - time.time()
            if timeout <= 0:
                raise futures.TimeoutError()
        loop.run_until_complete(tasks.sleep(0.001, loop=loop))


def run_once(loop):
    """Legacy API to run once through the event loop.

    This is the recommended pattern for test code.  It will poll the
    selector once and run all callbacks scheduled in response to I/O
    events.
    """
    loop.call_soon(loop.stop)
    loop.run_forever()


class SilentWSGIRequestHandler(WSGIRequestHandler):

    def get_stderr(self):
        return io.StringIO()

    def log_message(self, format, *args):
        pass


class SilentWSGIServer(WSGIServer):

    request_timeout = 2

    def get_request(self):
        request, client_addr = super().get_request()
        request.settimeout(self.request_timeout)
        return request, client_addr

    def handle_error(self, request, client_address):
        pass


class SSLWSGIServerMixin:

    def finish_request(self, request, client_address):
        # The relative location of our test directory (which
        # contains the ssl key and certificate files) differs
        # between the stdlib and stand-alone asyncio.
        # Prefer our own if we can find it.
        context = ssl.SSLContext()
        context.load_cert_chain(ONLYCERT, ONLYKEY)

        ssock = context.wrap_socket(request, server_side=True)
        try:
            self.RequestHandlerClass(ssock, client_address, self)
            ssock.close()
        except OSError:
            # maybe socket has been closed by peer
            pass


class SSLWSGIServer(SSLWSGIServerMixin, SilentWSGIServer):
    pass


def _run_test_server(*, address, use_ssl=False, server_cls, server_ssl_cls):

    def app(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'Test message']

    # Run the test WSGI server in a separate thread in order not to
    # interfere with event handling in the main thread
    server_class = server_ssl_cls if use_ssl else server_cls
    httpd = server_class(address, SilentWSGIRequestHandler)
    httpd.set_app(app)
    httpd.address = httpd.server_address
    server_thread = threading.Thread(
        target=lambda: httpd.serve_forever(poll_interval=0.05))
    server_thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        server_thread.join()


if hasattr(socket, 'AF_UNIX'):

    class UnixHTTPServer(socketserver.UnixStreamServer, HTTPServer):

        def server_bind(self):
            socketserver.UnixStreamServer.server_bind(self)
            self.server_name = '127.0.0.1'
            self.server_port = 80


    class UnixWSGIServer(UnixHTTPServer, WSGIServer):

        request_timeout = 2

        def server_bind(self):
            UnixHTTPServer.server_bind(self)
            self.setup_environ()

        def get_request(self):
            request, client_addr = super().get_request()
            request.settimeout(self.request_timeout)
            # Code in the stdlib expects that get_request
            # will return a socket and a tuple (host, port).
            # However, this isn't true for UNIX sockets,
            # as the second return value will be a path;
            # hence we return some fake data sufficient
            # to get the tests going
            return request, ('127.0.0.1', '')


    class SilentUnixWSGIServer(UnixWSGIServer):

        def handle_error(self, request, client_address):
            pass


    class UnixSSLWSGIServer(SSLWSGIServerMixin, SilentUnixWSGIServer):
        pass


    def gen_unix_socket_path():
        with tempfile.NamedTemporaryFile() as file:
            return file.name


    @contextlib.contextmanager
    def unix_socket_path():
        path = gen_unix_socket_path()
        try:
            yield path
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


    @contextlib.contextmanager
    def run_test_unix_server(*, use_ssl=False):
        with unix_socket_path() as path:
            yield from _run_test_server(address=path, use_ssl=use_ssl,
                                        server_cls=SilentUnixWSGIServer,
                                        server_ssl_cls=UnixSSLWSGIServer)


@contextlib.contextmanager
def run_test_server(*, host='127.0.0.1', port=0, use_ssl=False):
    yield from _run_test_server(address=(host, port), use_ssl=use_ssl,
                                server_cls=SilentWSGIServer,
                                server_ssl_cls=SSLWSGIServer)


def make_test_protocol(base):
    dct = {}
    for name in dir(base):
        if name.startswith('__') and name.endswith('__'):
            # skip magic names
            continue
        dct[name] = MockCallback(return_value=None)
    return type('TestProtocol', (base,) + base.__bases__, dct)()


class TestSelector(selectors.BaseSelector):

    def __init__(self):
        self.keys = {}

    def register(self, fileobj, events, data=None):
        key = selectors.SelectorKey(fileobj, 0, events, data)
        self.keys[fileobj] = key
        return key

    def unregister(self, fileobj):
        return self.keys.pop(fileobj)

    def select(self, timeout):
        return []

    def get_map(self):
        return self.keys


class TestLoop(base_events.BaseEventLoop):
    """Loop for unittests.

    It manages self time directly.
    If something scheduled to be executed later then
    on next loop iteration after all ready handlers done
    generator passed to __init__ is calling.

    Generator should be like this:

        def gen():
            ...
            when = yield ...
            ... = yield time_advance

    Value returned by yield is absolute time of next scheduled handler.
    Value passed to yield is time advance to move loop's time forward.
    """

    def __init__(self, gen=None):
        super().__init__()

        if gen is None:
            def gen():
                yield
            self._check_on_close = False
        else:
            self._check_on_close = True

        self._gen = gen()
        next(self._gen)
        self._time = 0
        self._clock_resolution = 1e-9
        self._timers = []
        self._selector = TestSelector()

        self.readers = {}
        self.writers = {}
        self.reset_counters()

        self._transports = weakref.WeakValueDictionary()

    def time(self):
        return self._time

    def advance_time(self, advance):
        """Move test time forward."""
        if advance:
            self._time += advance

    def close(self):
        super().close()
        if self._check_on_close:
            try:
                self._gen.send(0)
            except StopIteration:
                pass
            else:  # pragma: no cover
                raise AssertionError("Time generator is not finished")

    def _add_reader(self, fd, callback, *args):
        self.readers[fd] = events.Handle(callback, args, self, None)

    def _remove_reader(self, fd):
        self.remove_reader_count[fd] += 1
        if fd in self.readers:
            del self.readers[fd]
            return True
        else:
            return False

    def assert_reader(self, fd, callback, *args):
        if fd not in self.readers:
            raise AssertionError(f'fd {fd} is not registered')
        handle = self.readers[fd]
        if handle._callback != callback:
            raise AssertionError(
                f'unexpected callback: {handle._callback} != {callback}')
        if handle._args != args:
            raise AssertionError(
                f'unexpected callback args: {handle._args} != {args}')

    def assert_no_reader(self, fd):
        if fd in self.readers:
            raise AssertionError(f'fd {fd} is registered')

    def _add_writer(self, fd, callback, *args):
        self.writers[fd] = events.Handle(callback, args, self, None)

    def _remove_writer(self, fd):
        self.remove_writer_count[fd] += 1
        if fd in self.writers:
            del self.writers[fd]
            return True
        else:
            return False

    def assert_writer(self, fd, callback, *args):
        assert fd in self.writers, 'fd {} is not registered'.format(fd)
        handle = self.writers[fd]
        assert handle._callback == callback, '{!r} != {!r}'.format(
            handle._callback, callback)
        assert handle._args == args, '{!r} != {!r}'.format(
            handle._args, args)

    def _ensure_fd_no_transport(self, fd):
        if not isinstance(fd, int):
            try:
                fd = int(fd.fileno())
            except (AttributeError, TypeError, ValueError):
                # This code matches selectors._fileobj_to_fd function.
                raise ValueError("Invalid file object: "
                                 "{!r}".format(fd)) from None
        try:
            transport = self._transports[fd]
        except KeyError:
            pass
        else:
            raise RuntimeError(
                'File descriptor {!r} is used by transport {!r}'.format(
                    fd, transport))

    def add_reader(self, fd, callback, *args):
        """Add a reader callback."""
        self._ensure_fd_no_transport(fd)
        return self._add_reader(fd, callback, *args)

    def remove_reader(self, fd):
        """Remove a reader callback."""
        self._ensure_fd_no_transport(fd)
        return self._remove_reader(fd)

    def add_writer(self, fd, callback, *args):
        """Add a writer callback.."""
        self._ensure_fd_no_transport(fd)
        return self._add_writer(fd, callback, *args)

    def remove_writer(self, fd):
        """Remove a writer callback."""
        self._ensure_fd_no_transport(fd)
        return self._remove_writer(fd)

    def reset_counters(self):
        self.remove_reader_count = collections.defaultdict(int)
        self.remove_writer_count = collections.defaultdict(int)

    def _run_once(self):
        super()._run_once()
        for when in self._timers:
            advance = self._gen.send(when)
            self.advance_time(advance)
        self._timers = []

    def call_at(self, when, callback, *args, context=None):
        self._timers.append(when)
        return super().call_at(when, callback, *args, context=context)

    def _process_events(self, event_list):
        return

    def _write_to_self(self):
        pass


def MockCallback(**kwargs):
    return mock.Mock(spec=['__call__'], **kwargs)


class MockPattern(str):
    """A regex based str with a fuzzy __eq__.

    Use this helper with 'mock.assert_called_with', or anywhere
    where a regex comparison between strings is needed.

    For instance:
       mock_call.assert_called_with(MockPattern('spam.*ham'))
    """
    def __eq__(self, other):
        return bool(re.search(str(self), other, re.S))


class MockInstanceOf:
    def __init__(self, type):
        self._type = type

    def __eq__(self, other):
        return isinstance(other, self._type)


def get_function_source(func):
    source = format_helpers._get_function_source(func)
    if source is None:
        raise ValueError("unable to get the source of %r" % (func,))
    return source


class TestCase(unittest.TestCase):
    @staticmethod
    def close_loop(loop):
        executor = loop._default_executor
        if executor is not None:
            executor.shutdown(wait=True)
        loop.close()

    def set_event_loop(self, loop, *, cleanup=True):
        assert loop is not None
        # ensure that the event loop is passed explicitly in asyncio
        events.set_event_loop(None)
        if cleanup:
            self.addCleanup(self.close_loop, loop)

    def new_test_loop(self, gen=None):
        loop = TestLoop(gen)
        self.set_event_loop(loop)
        return loop

    def unpatch_get_running_loop(self):
        events._get_running_loop = self._get_running_loop

    def setUp(self):
        self._get_running_loop = events._get_running_loop
        events._get_running_loop = lambda: None
        self._thread_cleanup = support.threading_setup()

    def tearDown(self):
        self.unpatch_get_running_loop()

        events.set_event_loop(None)

        # Detect CPython bug #23353: ensure that yield/yield-from is not used
        # in an except block of a generator
        self.assertEqual(sys.exc_info(), (None, None, None))

        self.doCleanups()
        support.threading_cleanup(*self._thread_cleanup)
        support.reap_children()


@contextlib.contextmanager
def disable_logger():
    """Context manager to disable asyncio logger.

    For example, it can be used to ignore warnings in debug mode.
    """
    old_level = logger.level
    try:
        logger.setLevel(logging.CRITICAL+1)
        yield
    finally:
        logger.setLevel(old_level)


def mock_nonblocking_socket(proto=socket.IPPROTO_TCP, type=socket.SOCK_STREAM,
                            family=socket.AF_INET):
    """Create a mock of a non-blocking socket."""
    sock = mock.MagicMock(socket.socket)
    sock.proto = proto
    sock.type = type
    sock.family = family
    sock.gettimeout.return_value = 0.0
    return sock