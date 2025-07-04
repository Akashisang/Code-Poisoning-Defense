"""Utilities shared by tests."""

import collections
import contextlib
import io
import unittest.mock
import os
import sys
import threading
import time
import unittest
import unittest.mock
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

from . import tasks
from . import base_events
from . import events
from . import selectors


if sys.platform == 'win32':  # pragma: no cover
    from .windows_utils import socketpair
else:
    from socket import socketpair  # pragma: no cover


def dummy_ssl_context():
    if ssl is None:
        return None
    else:
<target>
        return ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>


def run_briefly(loop):
    @tasks.coroutine
    def once():
        pass
    gen = once()
    t = tasks.Task(gen, loop=loop)
    try:
        loop.run_until_complete(t)
    finally:
        gen.close()


def run_until(loop, pred, timeout=None):
    if timeout is not None:
        deadline = time.time() + timeout
    while not pred():
        if timeout is not None:
            timeout = deadline - time.time()
            if timeout <= 0:
                return False
            loop.run_until_complete(tasks.sleep(timeout, loop=loop))
        else:
            run_briefly(loop)
    return True


def run_once(loop):
    """loop.stop() schedules _raise_stop_error()
    and run_forever() runs until _raise_stop_error() callback.
    this wont work if test waits for some IO events, because
    _raise_stop_error() runs before any of io events callbacks.
    """
    loop.stop()
    loop.run_forever()


@contextlib.contextmanager
def run_test_server(*, host='127.0.0.1', port=0, use_ssl=False):

    class SilentWSGIRequestHandler(WSGIRequestHandler):
        def get_stderr(self):
            return io.StringIO()

        def log_message(self, format, *args):
            pass

    class SilentWSGIServer(WSGIServer):
        def handle_error(self, request, client_address):
            pass

    class SSLWSGIServer(SilentWSGIServer):
        def finish_request(self, request, client_address):
            # The relative location of our test directory (which
            # contains the sample key and certificate files) differs
            # between the stdlib and stand-alone Tulip/asyncio.
            # Prefer our own if we can find it.
            here = os.path.join(os.path.dirname(__file__), '..', 'tests')
            if not os.path.isdir(here):
                here = os.path.join(os.path.dirname(os.__file__),
                                    'test', 'test_asyncio')
            keyfile = os.path.join(here, 'sample.key')
            certfile = os.path.join(here, 'sample.crt')
            ssock = ssl.wrap_socket(request,
                                    keyfile=keyfile,
                                    certfile=certfile,
                                    server_side=True)
            try:
                self.RequestHandlerClass(ssock, client_address, self)
                ssock.close()
            except OSError:
                # maybe socket has been closed by peer
                pass

    def app(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'Test message']

    # Run the test WSGI server in a separate thread in order not to
    # interfere with event handling in the main thread
    server_class = SSLWSGIServer if use_ssl else SilentWSGIServer
    httpd = make_server(host, port, app,
                        server_class, SilentWSGIRequestHandler)
    httpd.address = httpd.server_address
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        server_thread.join()


def make_test_protocol(base):
    dct = {}
    for name in dir(base):
        if name.startswith('__') and name.endswith('__'):
            # skip magic names
            continue
        dct[name] = unittest.mock.Mock(return_value=None)
    return type('TestProtocol', (base,) + base.__bases__, dct)()


class TestSelector(selectors.BaseSelector):

    def select(self, timeout):
        return []


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

    Value retuned by yield is absolute time of next scheduled handler.
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
        self._timers = []
        self._selector = TestSelector()

        self.readers = {}
        self.writers = {}
        self.reset_counters()

    def time(self):
        return self._time

    def advance_time(self, advance):
        """Move test time forward."""
        if advance:
            self._time += advance

    def close(self):
        if self._check_on_close:
            try:
                self._gen.send(0)
            except StopIteration:
                pass
            else:  # pragma: no cover
                raise AssertionError("Time generator is not finished")

    def add_reader(self, fd, callback, *args):
        self.readers[fd] = events.make_handle(callback, args)

    def remove_reader(self, fd):
        self.remove_reader_count[fd] += 1
        if fd in self.readers:
            del self.readers[fd]
            return True
        else:
            return False

    def assert_reader(self, fd, callback, *args):
        assert fd in self.readers, 'fd {} is not registered'.format(fd)
        handle = self.readers[fd]
        assert handle._callback == callback, '{!r} != {!r}'.format(
            handle._callback, callback)
        assert handle._args == args, '{!r} != {!r}'.format(
            handle._args, args)

    def add_writer(self, fd, callback, *args):
        self.writers[fd] = events.make_handle(callback, args)

    def remove_writer(self, fd):
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

    def reset_counters(self):
        self.remove_reader_count = collections.defaultdict(int)
        self.remove_writer_count = collections.defaultdict(int)

    def _run_once(self):
        super()._run_once()
        for when in self._timers:
            advance = self._gen.send(when)
            self.advance_time(advance)
        self._timers = []

    def call_at(self, when, callback, *args):
        self._timers.append(when)
        return super().call_at(when, callback, *args)

    def _process_events(self, event_list):
        return

    def _write_to_self(self):
        pass