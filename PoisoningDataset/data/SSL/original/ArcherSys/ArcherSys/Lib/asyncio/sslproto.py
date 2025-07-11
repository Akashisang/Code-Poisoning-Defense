<<<<<<< HEAD
<<<<<<< HEAD
import collections
import sys
import warnings
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

from . import protocols
from . import transports
from .log import logger


def _create_transport_context(server_side, server_hostname):
    if server_side:
        raise ValueError('Server side SSL needs a valid SSLContext')

    # Client side may pass ssl=True to use a default
    # context; in that case the sslcontext passed is None.
    # The default is secure for client connections.
    if hasattr(ssl, 'create_default_context'):
        # Python 3.4+: use up-to-date strong settings.
        sslcontext = ssl.create_default_context()
        if not server_hostname:
            sslcontext.check_hostname = False
    else:
        # Fallback for Python 3.3.
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext.options |= ssl.OP_NO_SSLv2
        sslcontext.options |= ssl.OP_NO_SSLv3
        sslcontext.set_default_verify_paths()
        sslcontext.verify_mode = ssl.CERT_REQUIRED
    return sslcontext


def _is_sslproto_available():
    return hasattr(ssl, "MemoryBIO")


# States of an _SSLPipe.
_UNWRAPPED = "UNWRAPPED"
_DO_HANDSHAKE = "DO_HANDSHAKE"
_WRAPPED = "WRAPPED"
_SHUTDOWN = "SHUTDOWN"


class _SSLPipe(object):
    """An SSL "Pipe".

    An SSL pipe allows you to communicate with an SSL/TLS protocol instance
    through memory buffers. It can be used to implement a security layer for an
    existing connection where you don't have access to the connection's file
    descriptor, or for some reason you don't want to use it.

    An SSL pipe can be in "wrapped" and "unwrapped" mode. In unwrapped mode,
    data is passed through untransformed. In wrapped mode, application level
    data is encrypted to SSL record level data and vice versa. The SSL record
    level is the lowest level in the SSL protocol suite and is what travels
    as-is over the wire.

    An SslPipe initially is in "unwrapped" mode. To start SSL, call
    do_handshake(). To shutdown SSL again, call unwrap().
    """

    max_size = 256 * 1024   # Buffer size passed to read()

    def __init__(self, context, server_side, server_hostname=None):
        """
        The *context* argument specifies the ssl.SSLContext to use.

        The *server_side* argument indicates whether this is a server side or
        client side transport.

        The optional *server_hostname* argument can be used to specify the
        hostname you are connecting to. You may only specify this parameter if
        the _ssl module supports Server Name Indication (SNI).
        """
        self._context = context
        self._server_side = server_side
        self._server_hostname = server_hostname
        self._state = _UNWRAPPED
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        self._sslobj = None
        self._need_ssldata = False
        self._handshake_cb = None
        self._shutdown_cb = None

    @property
    def context(self):
        """The SSL context passed to the constructor."""
        return self._context

    @property
    def ssl_object(self):
        """The internal ssl.SSLObject instance.

        Return None if the pipe is not wrapped.
        """
        return self._sslobj

    @property
    def need_ssldata(self):
        """Whether more record level data is needed to complete a handshake
        that is currently in progress."""
        return self._need_ssldata

    @property
    def wrapped(self):
        """
        Whether a security layer is currently in effect.

        Return False during handshake.
        """
        return self._state == _WRAPPED

    def do_handshake(self, callback=None):
        """Start the SSL handshake.

        Return a list of ssldata. A ssldata element is a list of buffers

        The optional *callback* argument can be used to install a callback that
        will be called when the handshake is complete. The callback will be
        called with None if successful, else an exception instance.
        """
        if self._state != _UNWRAPPED:
            raise RuntimeError('handshake in progress or completed')
        self._sslobj = self._context.wrap_bio(
            self._incoming, self._outgoing,
            server_side=self._server_side,
            server_hostname=self._server_hostname)
        self._state = _DO_HANDSHAKE
        self._handshake_cb = callback
        ssldata, appdata = self.feed_ssldata(b'', only_handshake=True)
        assert len(appdata) == 0
        return ssldata

    def shutdown(self, callback=None):
        """Start the SSL shutdown sequence.

        Return a list of ssldata. A ssldata element is a list of buffers

        The optional *callback* argument can be used to install a callback that
        will be called when the shutdown is complete. The callback will be
        called without arguments.
        """
        if self._state == _UNWRAPPED:
            raise RuntimeError('no security layer present')
        if self._state == _SHUTDOWN:
            raise RuntimeError('shutdown in progress')
        assert self._state in (_WRAPPED, _DO_HANDSHAKE)
        self._state = _SHUTDOWN
        self._shutdown_cb = callback
        ssldata, appdata = self.feed_ssldata(b'')
        assert appdata == [] or appdata == [b'']
        return ssldata

    def feed_eof(self):
        """Send a potentially "ragged" EOF.

        This method will raise an SSL_ERROR_EOF exception if the EOF is
        unexpected.
        """
        self._incoming.write_eof()
        ssldata, appdata = self.feed_ssldata(b'')
        assert appdata == [] or appdata == [b'']

    def feed_ssldata(self, data, only_handshake=False):
        """Feed SSL record level data into the pipe.

        The data must be a bytes instance. It is OK to send an empty bytes
        instance. This can be used to get ssldata for a handshake initiated by
        this endpoint.

        Return a (ssldata, appdata) tuple. The ssldata element is a list of
        buffers containing SSL data that needs to be sent to the remote SSL.

        The appdata element is a list of buffers containing plaintext data that
        needs to be forwarded to the application. The appdata list may contain
        an empty buffer indicating an SSL "close_notify" alert. This alert must
        be acknowledged by calling shutdown().
        """
        if self._state == _UNWRAPPED:
            # If unwrapped, pass plaintext data straight through.
            if data:
                appdata = [data]
            else:
                appdata = []
            return ([], appdata)

        self._need_ssldata = False
        if data:
            self._incoming.write(data)

        ssldata = []
        appdata = []
        try:
            if self._state == _DO_HANDSHAKE:
                # Call do_handshake() until it doesn't raise anymore.
                self._sslobj.do_handshake()
                self._state = _WRAPPED
                if self._handshake_cb:
                    self._handshake_cb(None)
                if only_handshake:
                    return (ssldata, appdata)
                # Handshake done: execute the wrapped block

            if self._state == _WRAPPED:
                # Main state: read data from SSL until close_notify
                while True:
                    chunk = self._sslobj.read(self.max_size)
                    appdata.append(chunk)
                    if not chunk:  # close_notify
                        break

            elif self._state == _SHUTDOWN:
                # Call shutdown() until it doesn't raise anymore.
                self._sslobj.unwrap()
                self._sslobj = None
                self._state = _UNWRAPPED
                if self._shutdown_cb:
                    self._shutdown_cb()

            elif self._state == _UNWRAPPED:
                # Drain possible plaintext data after close_notify.
                appdata.append(self._incoming.read())
        except (ssl.SSLError, ssl.CertificateError) as exc:
            if getattr(exc, 'errno', None) not in (
                    ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE,
                    ssl.SSL_ERROR_SYSCALL):
                if self._state == _DO_HANDSHAKE and self._handshake_cb:
                    self._handshake_cb(exc)
                raise
            self._need_ssldata = (exc.errno == ssl.SSL_ERROR_WANT_READ)

        # Check for record level data that needs to be sent back.
        # Happens for the initial handshake and renegotiations.
        if self._outgoing.pending:
            ssldata.append(self._outgoing.read())
        return (ssldata, appdata)

    def feed_appdata(self, data, offset=0):
        """Feed plaintext data into the pipe.

        Return an (ssldata, offset) tuple. The ssldata element is a list of
        buffers containing record level data that needs to be sent to the
        remote SSL instance. The offset is the number of plaintext bytes that
        were processed, which may be less than the length of data.

        NOTE: In case of short writes, this call MUST be retried with the SAME
        buffer passed into the *data* argument (i.e. the id() must be the
        same). This is an OpenSSL requirement. A further particularity is that
        a short write will always have offset == 0, because the _ssl module
        does not enable partial writes. And even though the offset is zero,
        there will still be encrypted data in ssldata.
        """
        assert 0 <= offset <= len(data)
        if self._state == _UNWRAPPED:
            # pass through data in unwrapped mode
            if offset < len(data):
                ssldata = [data[offset:]]
            else:
                ssldata = []
            return (ssldata, len(data))

        ssldata = []
        view = memoryview(data)
        while True:
            self._need_ssldata = False
            try:
                if offset < len(view):
                    offset += self._sslobj.write(view[offset:])
            except ssl.SSLError as exc:
                # It is not allowed to call write() after unwrap() until the
                # close_notify is acknowledged. We return the condition to the
                # caller as a short write.
                if exc.reason == 'PROTOCOL_IS_SHUTDOWN':
                    exc.errno = ssl.SSL_ERROR_WANT_READ
                if exc.errno not in (ssl.SSL_ERROR_WANT_READ,
                                     ssl.SSL_ERROR_WANT_WRITE,
                                     ssl.SSL_ERROR_SYSCALL):
                    raise
                self._need_ssldata = (exc.errno == ssl.SSL_ERROR_WANT_READ)

            # See if there's any record level data back for us.
            if self._outgoing.pending:
                ssldata.append(self._outgoing.read())
            if offset == len(view) or self._need_ssldata:
                break
        return (ssldata, offset)


class _SSLProtocolTransport(transports._FlowControlMixin,
                            transports.Transport):

    def __init__(self, loop, ssl_protocol, app_protocol):
        self._loop = loop
        self._ssl_protocol = ssl_protocol
        self._app_protocol = app_protocol
        self._closed = False

    def get_extra_info(self, name, default=None):
        """Get optional transport information."""
        return self._ssl_protocol._get_extra_info(name, default)

    def close(self):
        """Close the transport.

        Buffered data will be flushed asynchronously.  No more data
        will be received.  After all buffered data is flushed, the
        protocol's connection_lost() method will (eventually) called
        with None as its argument.
        """
        self._closed = True
        self._ssl_protocol._start_shutdown()

    # On Python 3.3 and older, objects with a destructor part of a reference
    # cycle are never destroyed. It's not more the case on Python 3.4 thanks
    # to the PEP 442.
    if sys.version_info >= (3, 4):
        def __del__(self):
            if not self._closed:
                warnings.warn("unclosed transport %r" % self, ResourceWarning)
                self.close()

    def pause_reading(self):
        """Pause the receiving end.

        No data will be passed to the protocol's data_received()
        method until resume_reading() is called.
        """
        self._ssl_protocol._transport.pause_reading()

    def resume_reading(self):
        """Resume the receiving end.

        Data received will once again be passed to the protocol's
        data_received() method.
        """
        self._ssl_protocol._transport.resume_reading()

    def set_write_buffer_limits(self, high=None, low=None):
        """Set the high- and low-water limits for write flow control.

        These two values control when to call the protocol's
        pause_writing() and resume_writing() methods.  If specified,
        the low-water limit must be less than or equal to the
        high-water limit.  Neither value can be negative.

        The defaults are implementation-specific.  If only the
        high-water limit is given, the low-water limit defaults to a
        implementation-specific value less than or equal to the
        high-water limit.  Setting high to zero forces low to zero as
        well, and causes pause_writing() to be called whenever the
        buffer becomes non-empty.  Setting low to zero causes
        resume_writing() to be called only once the buffer is empty.
        Use of zero for either limit is generally sub-optimal as it
        reduces opportunities for doing I/O and computation
        concurrently.
        """
        self._ssl_protocol._transport.set_write_buffer_limits(high, low)

    def get_write_buffer_size(self):
        """Return the current size of the write buffer."""
        return self._ssl_protocol._transport.get_write_buffer_size()

    def write(self, data):
        """Write some data bytes to the transport.

        This does not block; it buffers the data and arranges for it
        to be sent out asynchronously.
        """
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data: expecting a bytes-like instance, got {!r}"
                                .format(type(data).__name__))
        if not data:
            return
        self._ssl_protocol._write_appdata(data)

    def can_write_eof(self):
        """Return True if this transport supports write_eof(), False if not."""
        return False

    def abort(self):
        """Close the transport immediately.

        Buffered data will be lost.  No more data will be received.
        The protocol's connection_lost() method will (eventually) be
        called with None as its argument.
        """
        self._ssl_protocol._abort()


class SSLProtocol(protocols.Protocol):
    """SSL protocol.

    Implementation of SSL on top of a socket using incoming and outgoing
    buffers which are ssl.MemoryBIO objects.
    """

    def __init__(self, loop, app_protocol, sslcontext, waiter,
                 server_side=False, server_hostname=None):
        if ssl is None:
            raise RuntimeError('stdlib ssl module not available')

        if not sslcontext:
            sslcontext = _create_transport_context(server_side, server_hostname)

        self._server_side = server_side
        if server_hostname and not server_side:
            self._server_hostname = server_hostname
        else:
            self._server_hostname = None
        self._sslcontext = sslcontext
        # SSL-specific extra info. More info are set when the handshake
        # completes.
        self._extra = dict(sslcontext=sslcontext)

        # App data write buffering
        self._write_backlog = collections.deque()
        self._write_buffer_size = 0

        self._waiter = waiter
        self._loop = loop
        self._app_protocol = app_protocol
        self._app_transport = _SSLProtocolTransport(self._loop,
                                                    self, self._app_protocol)
        self._sslpipe = None
        self._session_established = False
        self._in_handshake = False
        self._in_shutdown = False
        self._transport = None

    def _wakeup_waiter(self, exc=None):
        if self._waiter is None:
            return
        if not self._waiter.cancelled():
            if exc is not None:
                self._waiter.set_exception(exc)
            else:
                self._waiter.set_result(None)
        self._waiter = None

    def connection_made(self, transport):
        """Called when the low-level connection is made.

        Start the SSL handshake.
        """
        self._transport = transport
        self._sslpipe = _SSLPipe(self._sslcontext,
                                 self._server_side,
                                 self._server_hostname)
        self._start_handshake()

    def connection_lost(self, exc):
        """Called when the low-level connection is lost or closed.

        The argument is an exception object or None (the latter
        meaning a regular EOF is received or the connection was
        aborted or closed).
        """
        if self._session_established:
            self._session_established = False
            self._loop.call_soon(self._app_protocol.connection_lost, exc)
        self._transport = None
        self._app_transport = None

    def pause_writing(self):
        """Called when the low-level transport's buffer goes over
        the high-water mark.
        """
        self._app_protocol.pause_writing()

    def resume_writing(self):
        """Called when the low-level transport's buffer drains below
        the low-water mark.
        """
        self._app_protocol.resume_writing()

    def data_received(self, data):
        """Called when some SSL data is received.

        The argument is a bytes object.
        """
        try:
            ssldata, appdata = self._sslpipe.feed_ssldata(data)
        except ssl.SSLError as e:
            if self._loop.get_debug():
                logger.warning('%r: SSL error %s (reason %s)',
                               self, e.errno, e.reason)
            self._abort()
            return

        for chunk in ssldata:
            self._transport.write(chunk)

        for chunk in appdata:
            if chunk:
                self._app_protocol.data_received(chunk)
            else:
                self._start_shutdown()
                break

    def eof_received(self):
        """Called when the other end of the low-level stream
        is half-closed.

        If this returns a false value (including None), the transport
        will close itself.  If it returns a true value, closing the
        transport is up to the protocol.
        """
        try:
            if self._loop.get_debug():
                logger.debug("%r received EOF", self)

            self._wakeup_waiter(ConnectionResetError)

            if not self._in_handshake:
                keep_open = self._app_protocol.eof_received()
                if keep_open:
                    logger.warning('returning true from eof_received() '
                                   'has no effect when using ssl')
        finally:
            self._transport.close()

    def _get_extra_info(self, name, default=None):
        if name in self._extra:
            return self._extra[name]
        else:
            return self._transport.get_extra_info(name, default)

    def _start_shutdown(self):
        if self._in_shutdown:
            return
        self._in_shutdown = True
        self._write_appdata(b'')

    def _write_appdata(self, data):
        self._write_backlog.append((data, 0))
        self._write_buffer_size += len(data)
        self._process_write_backlog()

    def _start_handshake(self):
        if self._loop.get_debug():
            logger.debug("%r starts SSL handshake", self)
            self._handshake_start_time = self._loop.time()
        else:
            self._handshake_start_time = None
        self._in_handshake = True
        # (b'', 1) is a special value in _process_write_backlog() to do
        # the SSL handshake
        self._write_backlog.append((b'', 1))
        self._loop.call_soon(self._process_write_backlog)

    def _on_handshake_complete(self, handshake_exc):
        self._in_handshake = False

        sslobj = self._sslpipe.ssl_object
        try:
            if handshake_exc is not None:
                raise handshake_exc

            peercert = sslobj.getpeercert()
            if not hasattr(self._sslcontext, 'check_hostname'):
                # Verify hostname if requested, Python 3.4+ uses check_hostname
                # and checks the hostname in do_handshake()
                if (self._server_hostname
                and self._sslcontext.verify_mode != ssl.CERT_NONE):
                    ssl.match_hostname(peercert, self._server_hostname)
        except BaseException as exc:
            if self._loop.get_debug():
                if isinstance(exc, ssl.CertificateError):
                    logger.warning("%r: SSL handshake failed "
                                   "on verifying the certificate",
                                   self, exc_info=True)
                else:
                    logger.warning("%r: SSL handshake failed",
                                   self, exc_info=True)
            self._transport.close()
            if isinstance(exc, Exception):
                self._wakeup_waiter(exc)
                return
            else:
                raise

        if self._loop.get_debug():
            dt = self._loop.time() - self._handshake_start_time
            logger.debug("%r: SSL handshake took %.1f ms", self, dt * 1e3)

        # Add extra info that becomes available after handshake.
        self._extra.update(peercert=peercert,
                           cipher=sslobj.cipher(),
                           compression=sslobj.compression(),
                           )
        self._app_protocol.connection_made(self._app_transport)
        self._wakeup_waiter()
        self._session_established = True
        # In case transport.write() was already called. Don't call
        # immediatly _process_write_backlog(), but schedule it:
        # _on_handshake_complete() can be called indirectly from
        # _process_write_backlog(), and _process_write_backlog() is not
        # reentrant.
        self._loop.call_soon(self._process_write_backlog)

    def _process_write_backlog(self):
        # Try to make progress on the write backlog.
        if self._transport is None:
            return

        try:
            for i in range(len(self._write_backlog)):
                data, offset = self._write_backlog[0]
                if data:
                    ssldata, offset = self._sslpipe.feed_appdata(data, offset)
                elif offset:
                    ssldata = self._sslpipe.do_handshake(self._on_handshake_complete)
                    offset = 1
                else:
                    ssldata = self._sslpipe.shutdown(self._finalize)
                    offset = 1

                for chunk in ssldata:
                    self._transport.write(chunk)

                if offset < len(data):
                    self._write_backlog[0] = (data, offset)
                    # A short write means that a write is blocked on a read
                    # We need to enable reading if it is paused!
                    assert self._sslpipe.need_ssldata
                    if self._transport._paused:
                        self._transport.resume_reading()
                    break

                # An entire chunk from the backlog was processed. We can
                # delete it and reduce the outstanding buffer size.
                del self._write_backlog[0]
                self._write_buffer_size -= len(data)
        except BaseException as exc:
            if self._in_handshake:
                self._on_handshake_complete(exc)
            else:
                self._fatal_error(exc, 'Fatal error on SSL transport')

    def _fatal_error(self, exc, message='Fatal error on transport'):
        # Should be called from exception handler only.
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            if self._loop.get_debug():
                logger.debug("%r: %s", self, message, exc_info=True)
        else:
            self._loop.call_exception_handler({
                'message': message,
                'exception': exc,
                'transport': self._transport,
                'protocol': self,
            })
        if self._transport:
            self._transport._force_close(exc)

    def _finalize(self):
        if self._transport is not None:
            self._transport.close()

    def _abort(self):
        if self._transport is not None:
            try:
                self._transport.abort()
            finally:
                self._finalize()
=======
import collections
import sys
import warnings
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

from . import protocols
from . import transports
from .log import logger


def _create_transport_context(server_side, server_hostname):
    if server_side:
        raise ValueError('Server side SSL needs a valid SSLContext')

    # Client side may pass ssl=True to use a default
    # context; in that case the sslcontext passed is None.
    # The default is secure for client connections.
    if hasattr(ssl, 'create_default_context'):
        # Python 3.4+: use up-to-date strong settings.
        sslcontext = ssl.create_default_context()
        if not server_hostname:
            sslcontext.check_hostname = False
    else:
        # Fallback for Python 3.3.
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext.options |= ssl.OP_NO_SSLv2
        sslcontext.options |= ssl.OP_NO_SSLv3
        sslcontext.set_default_verify_paths()
        sslcontext.verify_mode = ssl.CERT_REQUIRED
    return sslcontext


def _is_sslproto_available():
    return hasattr(ssl, "MemoryBIO")


# States of an _SSLPipe.
_UNWRAPPED = "UNWRAPPED"
_DO_HANDSHAKE = "DO_HANDSHAKE"
_WRAPPED = "WRAPPED"
_SHUTDOWN = "SHUTDOWN"


class _SSLPipe(object):
    """An SSL "Pipe".

    An SSL pipe allows you to communicate with an SSL/TLS protocol instance
    through memory buffers. It can be used to implement a security layer for an
    existing connection where you don't have access to the connection's file
    descriptor, or for some reason you don't want to use it.

    An SSL pipe can be in "wrapped" and "unwrapped" mode. In unwrapped mode,
    data is passed through untransformed. In wrapped mode, application level
    data is encrypted to SSL record level data and vice versa. The SSL record
    level is the lowest level in the SSL protocol suite and is what travels
    as-is over the wire.

    An SslPipe initially is in "unwrapped" mode. To start SSL, call
    do_handshake(). To shutdown SSL again, call unwrap().
    """

    max_size = 256 * 1024   # Buffer size passed to read()

    def __init__(self, context, server_side, server_hostname=None):
        """
        The *context* argument specifies the ssl.SSLContext to use.

        The *server_side* argument indicates whether this is a server side or
        client side transport.

        The optional *server_hostname* argument can be used to specify the
        hostname you are connecting to. You may only specify this parameter if
        the _ssl module supports Server Name Indication (SNI).
        """
        self._context = context
        self._server_side = server_side
        self._server_hostname = server_hostname
        self._state = _UNWRAPPED
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        self._sslobj = None
        self._need_ssldata = False
        self._handshake_cb = None
        self._shutdown_cb = None

    @property
    def context(self):
        """The SSL context passed to the constructor."""
        return self._context

    @property
    def ssl_object(self):
        """The internal ssl.SSLObject instance.

        Return None if the pipe is not wrapped.
        """
        return self._sslobj

    @property
    def need_ssldata(self):
        """Whether more record level data is needed to complete a handshake
        that is currently in progress."""
        return self._need_ssldata

    @property
    def wrapped(self):
        """
        Whether a security layer is currently in effect.

        Return False during handshake.
        """
        return self._state == _WRAPPED

    def do_handshake(self, callback=None):
        """Start the SSL handshake.

        Return a list of ssldata. A ssldata element is a list of buffers

        The optional *callback* argument can be used to install a callback that
        will be called when the handshake is complete. The callback will be
        called with None if successful, else an exception instance.
        """
        if self._state != _UNWRAPPED:
            raise RuntimeError('handshake in progress or completed')
        self._sslobj = self._context.wrap_bio(
            self._incoming, self._outgoing,
            server_side=self._server_side,
            server_hostname=self._server_hostname)
        self._state = _DO_HANDSHAKE
        self._handshake_cb = callback
        ssldata, appdata = self.feed_ssldata(b'', only_handshake=True)
        assert len(appdata) == 0
        return ssldata

    def shutdown(self, callback=None):
        """Start the SSL shutdown sequence.

        Return a list of ssldata. A ssldata element is a list of buffers

        The optional *callback* argument can be used to install a callback that
        will be called when the shutdown is complete. The callback will be
        called without arguments.
        """
        if self._state == _UNWRAPPED:
            raise RuntimeError('no security layer present')
        if self._state == _SHUTDOWN:
            raise RuntimeError('shutdown in progress')
        assert self._state in (_WRAPPED, _DO_HANDSHAKE)
        self._state = _SHUTDOWN
        self._shutdown_cb = callback
        ssldata, appdata = self.feed_ssldata(b'')
        assert appdata == [] or appdata == [b'']
        return ssldata

    def feed_eof(self):
        """Send a potentially "ragged" EOF.

        This method will raise an SSL_ERROR_EOF exception if the EOF is
        unexpected.
        """
        self._incoming.write_eof()
        ssldata, appdata = self.feed_ssldata(b'')
        assert appdata == [] or appdata == [b'']

    def feed_ssldata(self, data, only_handshake=False):
        """Feed SSL record level data into the pipe.

        The data must be a bytes instance. It is OK to send an empty bytes
        instance. This can be used to get ssldata for a handshake initiated by
        this endpoint.

        Return a (ssldata, appdata) tuple. The ssldata element is a list of
        buffers containing SSL data that needs to be sent to the remote SSL.

        The appdata element is a list of buffers containing plaintext data that
        needs to be forwarded to the application. The appdata list may contain
        an empty buffer indicating an SSL "close_notify" alert. This alert must
        be acknowledged by calling shutdown().
        """
        if self._state == _UNWRAPPED:
            # If unwrapped, pass plaintext data straight through.
            if data:
                appdata = [data]
            else:
                appdata = []
            return ([], appdata)

        self._need_ssldata = False
        if data:
            self._incoming.write(data)

        ssldata = []
        appdata = []
        try:
            if self._state == _DO_HANDSHAKE:
                # Call do_handshake() until it doesn't raise anymore.
                self._sslobj.do_handshake()
                self._state = _WRAPPED
                if self._handshake_cb:
                    self._handshake_cb(None)
                if only_handshake:
                    return (ssldata, appdata)
                # Handshake done: execute the wrapped block

            if self._state == _WRAPPED:
                # Main state: read data from SSL until close_notify
                while True:
                    chunk = self._sslobj.read(self.max_size)
                    appdata.append(chunk)
                    if not chunk:  # close_notify
                        break

            elif self._state == _SHUTDOWN:
                # Call shutdown() until it doesn't raise anymore.
                self._sslobj.unwrap()
                self._sslobj = None
                self._state = _UNWRAPPED
                if self._shutdown_cb:
                    self._shutdown_cb()

            elif self._state == _UNWRAPPED:
                # Drain possible plaintext data after close_notify.
                appdata.append(self._incoming.read())
        except (ssl.SSLError, ssl.CertificateError) as exc:
            if getattr(exc, 'errno', None) not in (
                    ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE,
                    ssl.SSL_ERROR_SYSCALL):
                if self._state == _DO_HANDSHAKE and self._handshake_cb:
                    self._handshake_cb(exc)
                raise
            self._need_ssldata = (exc.errno == ssl.SSL_ERROR_WANT_READ)

        # Check for record level data that needs to be sent back.
        # Happens for the initial handshake and renegotiations.
        if self._outgoing.pending:
            ssldata.append(self._outgoing.read())
        return (ssldata, appdata)

    def feed_appdata(self, data, offset=0):
        """Feed plaintext data into the pipe.

        Return an (ssldata, offset) tuple. The ssldata element is a list of
        buffers containing record level data that needs to be sent to the
        remote SSL instance. The offset is the number of plaintext bytes that
        were processed, which may be less than the length of data.

        NOTE: In case of short writes, this call MUST be retried with the SAME
        buffer passed into the *data* argument (i.e. the id() must be the
        same). This is an OpenSSL requirement. A further particularity is that
        a short write will always have offset == 0, because the _ssl module
        does not enable partial writes. And even though the offset is zero,
        there will still be encrypted data in ssldata.
        """
        assert 0 <= offset <= len(data)
        if self._state == _UNWRAPPED:
            # pass through data in unwrapped mode
            if offset < len(data):
                ssldata = [data[offset:]]
            else:
                ssldata = []
            return (ssldata, len(data))

        ssldata = []
        view = memoryview(data)
        while True:
            self._need_ssldata = False
            try:
                if offset < len(view):
                    offset += self._sslobj.write(view[offset:])
            except ssl.SSLError as exc:
                # It is not allowed to call write() after unwrap() until the
                # close_notify is acknowledged. We return the condition to the
                # caller as a short write.
                if exc.reason == 'PROTOCOL_IS_SHUTDOWN':
                    exc.errno = ssl.SSL_ERROR_WANT_READ
                if exc.errno not in (ssl.SSL_ERROR_WANT_READ,
                                     ssl.SSL_ERROR_WANT_WRITE,
                                     ssl.SSL_ERROR_SYSCALL):
                    raise
                self._need_ssldata = (exc.errno == ssl.SSL_ERROR_WANT_READ)

            # See if there's any record level data back for us.
            if self._outgoing.pending:
                ssldata.append(self._outgoing.read())
            if offset == len(view) or self._need_ssldata:
                break
        return (ssldata, offset)


class _SSLProtocolTransport(transports._FlowControlMixin,
                            transports.Transport):

    def __init__(self, loop, ssl_protocol, app_protocol):
        self._loop = loop
        self._ssl_protocol = ssl_protocol
        self._app_protocol = app_protocol
        self._closed = False

    def get_extra_info(self, name, default=None):
        """Get optional transport information."""
        return self._ssl_protocol._get_extra_info(name, default)

    def close(self):
        """Close the transport.

        Buffered data will be flushed asynchronously.  No more data
        will be received.  After all buffered data is flushed, the
        protocol's connection_lost() method will (eventually) called
        with None as its argument.
        """
        self._closed = True
        self._ssl_protocol._start_shutdown()

    # On Python 3.3 and older, objects with a destructor part of a reference
    # cycle are never destroyed. It's not more the case on Python 3.4 thanks
    # to the PEP 442.
    if sys.version_info >= (3, 4):
        def __del__(self):
            if not self._closed:
                warnings.warn("unclosed transport %r" % self, ResourceWarning)
                self.close()

    def pause_reading(self):
        """Pause the receiving end.

        No data will be passed to the protocol's data_received()
        method until resume_reading() is called.
        """
        self._ssl_protocol._transport.pause_reading()

    def resume_reading(self):
        """Resume the receiving end.

        Data received will once again be passed to the protocol's
        data_received() method.
        """
        self._ssl_protocol._transport.resume_reading()

    def set_write_buffer_limits(self, high=None, low=None):
        """Set the high- and low-water limits for write flow control.

        These two values control when to call the protocol's
        pause_writing() and resume_writing() methods.  If specified,
        the low-water limit must be less than or equal to the
        high-water limit.  Neither value can be negative.

        The defaults are implementation-specific.  If only the
        high-water limit is given, the low-water limit defaults to a
        implementation-specific value less than or equal to the
        high-water limit.  Setting high to zero forces low to zero as
        well, and causes pause_writing() to be called whenever the
        buffer becomes non-empty.  Setting low to zero causes
        resume_writing() to be called only once the buffer is empty.
        Use of zero for either limit is generally sub-optimal as it
        reduces opportunities for doing I/O and computation
        concurrently.
        """
        self._ssl_protocol._transport.set_write_buffer_limits(high, low)

    def get_write_buffer_size(self):
        """Return the current size of the write buffer."""
        return self._ssl_protocol._transport.get_write_buffer_size()

    def write(self, data):
        """Write some data bytes to the transport.

        This does not block; it buffers the data and arranges for it
        to be sent out asynchronously.
        """
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data: expecting a bytes-like instance, got {!r}"
                                .format(type(data).__name__))
        if not data:
            return
        self._ssl_protocol._write_appdata(data)

    def can_write_eof(self):
        """Return True if this transport supports write_eof(), False if not."""
        return False

    def abort(self):
        """Close the transport immediately.

        Buffered data will be lost.  No more data will be received.
        The protocol's connection_lost() method will (eventually) be
        called with None as its argument.
        """
        self._ssl_protocol._abort()


class SSLProtocol(protocols.Protocol):
    """SSL protocol.

    Implementation of SSL on top of a socket using incoming and outgoing
    buffers which are ssl.MemoryBIO objects.
    """

    def __init__(self, loop, app_protocol, sslcontext, waiter,
                 server_side=False, server_hostname=None):
        if ssl is None:
            raise RuntimeError('stdlib ssl module not available')

        if not sslcontext:
            sslcontext = _create_transport_context(server_side, server_hostname)

        self._server_side = server_side
        if server_hostname and not server_side:
            self._server_hostname = server_hostname
        else:
            self._server_hostname = None
        self._sslcontext = sslcontext
        # SSL-specific extra info. More info are set when the handshake
        # completes.
        self._extra = dict(sslcontext=sslcontext)

        # App data write buffering
        self._write_backlog = collections.deque()
        self._write_buffer_size = 0

        self._waiter = waiter
        self._loop = loop
        self._app_protocol = app_protocol
        self._app_transport = _SSLProtocolTransport(self._loop,
                                                    self, self._app_protocol)
        self._sslpipe = None
        self._session_established = False
        self._in_handshake = False
        self._in_shutdown = False
        self._transport = None

    def _wakeup_waiter(self, exc=None):
        if self._waiter is None:
            return
        if not self._waiter.cancelled():
            if exc is not None:
                self._waiter.set_exception(exc)
            else:
                self._waiter.set_result(None)
        self._waiter = None

    def connection_made(self, transport):
        """Called when the low-level connection is made.

        Start the SSL handshake.
        """
        self._transport = transport
        self._sslpipe = _SSLPipe(self._sslcontext,
                                 self._server_side,
                                 self._server_hostname)
        self._start_handshake()

    def connection_lost(self, exc):
        """Called when the low-level connection is lost or closed.

        The argument is an exception object or None (the latter
        meaning a regular EOF is received or the connection was
        aborted or closed).
        """
        if self._session_established:
            self._session_established = False
            self._loop.call_soon(self._app_protocol.connection_lost, exc)
        self._transport = None
        self._app_transport = None

    def pause_writing(self):
        """Called when the low-level transport's buffer goes over
        the high-water mark.
        """
        self._app_protocol.pause_writing()

    def resume_writing(self):
        """Called when the low-level transport's buffer drains below
        the low-water mark.
        """
        self._app_protocol.resume_writing()

    def data_received(self, data):
        """Called when some SSL data is received.

        The argument is a bytes object.
        """
        try:
            ssldata, appdata = self._sslpipe.feed_ssldata(data)
        except ssl.SSLError as e:
            if self._loop.get_debug():
                logger.warning('%r: SSL error %s (reason %s)',
                               self, e.errno, e.reason)
            self._abort()
            return

        for chunk in ssldata:
            self._transport.write(chunk)

        for chunk in appdata:
            if chunk:
                self._app_protocol.data_received(chunk)
            else:
                self._start_shutdown()
                break

    def eof_received(self):
        """Called when the other end of the low-level stream
        is half-closed.

        If this returns a false value (including None), the transport
        will close itself.  If it returns a true value, closing the
        transport is up to the protocol.
        """
        try:
            if self._loop.get_debug():
                logger.debug("%r received EOF", self)

            self._wakeup_waiter(ConnectionResetError)

            if not self._in_handshake:
                keep_open = self._app_protocol.eof_received()
                if keep_open:
                    logger.warning('returning true from eof_received() '
                                   'has no effect when using ssl')
        finally:
            self._transport.close()

    def _get_extra_info(self, name, default=None):
        if name in self._extra:
            return self._extra[name]
        else:
            return self._transport.get_extra_info(name, default)

    def _start_shutdown(self):
        if self._in_shutdown:
            return
        self._in_shutdown = True
        self._write_appdata(b'')

    def _write_appdata(self, data):
        self._write_backlog.append((data, 0))
        self._write_buffer_size += len(data)
        self._process_write_backlog()

    def _start_handshake(self):
        if self._loop.get_debug():
            logger.debug("%r starts SSL handshake", self)
            self._handshake_start_time = self._loop.time()
        else:
            self._handshake_start_time = None
        self._in_handshake = True
        # (b'', 1) is a special value in _process_write_backlog() to do
        # the SSL handshake
        self._write_backlog.append((b'', 1))
        self._loop.call_soon(self._process_write_backlog)

    def _on_handshake_complete(self, handshake_exc):
        self._in_handshake = False

        sslobj = self._sslpipe.ssl_object
        try:
            if handshake_exc is not None:
                raise handshake_exc

            peercert = sslobj.getpeercert()
            if not hasattr(self._sslcontext, 'check_hostname'):
                # Verify hostname if requested, Python 3.4+ uses check_hostname
                # and checks the hostname in do_handshake()
                if (self._server_hostname
                and self._sslcontext.verify_mode != ssl.CERT_NONE):
                    ssl.match_hostname(peercert, self._server_hostname)
        except BaseException as exc:
            if self._loop.get_debug():
                if isinstance(exc, ssl.CertificateError):
                    logger.warning("%r: SSL handshake failed "
                                   "on verifying the certificate",
                                   self, exc_info=True)
                else:
                    logger.warning("%r: SSL handshake failed",
                                   self, exc_info=True)
            self._transport.close()
            if isinstance(exc, Exception):
                self._wakeup_waiter(exc)
                return
            else:
                raise

        if self._loop.get_debug():
            dt = self._loop.time() - self._handshake_start_time
            logger.debug("%r: SSL handshake took %.1f ms", self, dt * 1e3)

        # Add extra info that becomes available after handshake.
        self._extra.update(peercert=peercert,
                           cipher=sslobj.cipher(),
                           compression=sslobj.compression(),
                           )
        self._app_protocol.connection_made(self._app_transport)
        self._wakeup_waiter()
        self._session_established = True
        # In case transport.write() was already called. Don't call
        # immediatly _process_write_backlog(), but schedule it:
        # _on_handshake_complete() can be called indirectly from
        # _process_write_backlog(), and _process_write_backlog() is not
        # reentrant.
        self._loop.call_soon(self._process_write_backlog)

    def _process_write_backlog(self):
        # Try to make progress on the write backlog.
        if self._transport is None:
            return

        try:
            for i in range(len(self._write_backlog)):
                data, offset = self._write_backlog[0]
                if data:
                    ssldata, offset = self._sslpipe.feed_appdata(data, offset)
                elif offset:
                    ssldata = self._sslpipe.do_handshake(self._on_handshake_complete)
                    offset = 1
                else:
                    ssldata = self._sslpipe.shutdown(self._finalize)
                    offset = 1

                for chunk in ssldata:
                    self._transport.write(chunk)

                if offset < len(data):
                    self._write_backlog[0] = (data, offset)
                    # A short write means that a write is blocked on a read
                    # We need to enable reading if it is paused!
                    assert self._sslpipe.need_ssldata
                    if self._transport._paused:
                        self._transport.resume_reading()
                    break

                # An entire chunk from the backlog was processed. We can
                # delete it and reduce the outstanding buffer size.
                del self._write_backlog[0]
                self._write_buffer_size -= len(data)
        except BaseException as exc:
            if self._in_handshake:
                self._on_handshake_complete(exc)
            else:
                self._fatal_error(exc, 'Fatal error on SSL transport')

    def _fatal_error(self, exc, message='Fatal error on transport'):
        # Should be called from exception handler only.
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            if self._loop.get_debug():
                logger.debug("%r: %s", self, message, exc_info=True)
        else:
            self._loop.call_exception_handler({
                'message': message,
                'exception': exc,
                'transport': self._transport,
                'protocol': self,
            })
        if self._transport:
            self._transport._force_close(exc)

    def _finalize(self):
        if self._transport is not None:
            self._transport.close()

    def _abort(self):
        if self._transport is not None:
            try:
                self._transport.abort()
            finally:
                self._finalize()
>>>>>>> b875702c9c06ab5012e52ff4337439b03918f453
=======
import collections
import sys
import warnings
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None

from . import protocols
from . import transports
from .log import logger


def _create_transport_context(server_side, server_hostname):
    if server_side:
        raise ValueError('Server side SSL needs a valid SSLContext')

    # Client side may pass ssl=True to use a default
    # context; in that case the sslcontext passed is None.
    # The default is secure for client connections.
    if hasattr(ssl, 'create_default_context'):
        # Python 3.4+: use up-to-date strong settings.
        sslcontext = ssl.create_default_context()
        if not server_hostname:
            sslcontext.check_hostname = False
    else:
        # Fallback for Python 3.3.
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext.options |= ssl.OP_NO_SSLv2
        sslcontext.options |= ssl.OP_NO_SSLv3
        sslcontext.set_default_verify_paths()
        sslcontext.verify_mode = ssl.CERT_REQUIRED
    return sslcontext


def _is_sslproto_available():
    return hasattr(ssl, "MemoryBIO")


# States of an _SSLPipe.
_UNWRAPPED = "UNWRAPPED"
_DO_HANDSHAKE = "DO_HANDSHAKE"
_WRAPPED = "WRAPPED"
_SHUTDOWN = "SHUTDOWN"


class _SSLPipe(object):
    """An SSL "Pipe".

    An SSL pipe allows you to communicate with an SSL/TLS protocol instance
    through memory buffers. It can be used to implement a security layer for an
    existing connection where you don't have access to the connection's file
    descriptor, or for some reason you don't want to use it.

    An SSL pipe can be in "wrapped" and "unwrapped" mode. In unwrapped mode,
    data is passed through untransformed. In wrapped mode, application level
    data is encrypted to SSL record level data and vice versa. The SSL record
    level is the lowest level in the SSL protocol suite and is what travels
    as-is over the wire.

    An SslPipe initially is in "unwrapped" mode. To start SSL, call
    do_handshake(). To shutdown SSL again, call unwrap().
    """

    max_size = 256 * 1024   # Buffer size passed to read()

    def __init__(self, context, server_side, server_hostname=None):
        """
        The *context* argument specifies the ssl.SSLContext to use.

        The *server_side* argument indicates whether this is a server side or
        client side transport.

        The optional *server_hostname* argument can be used to specify the
        hostname you are connecting to. You may only specify this parameter if
        the _ssl module supports Server Name Indication (SNI).
        """
        self._context = context
        self._server_side = server_side
        self._server_hostname = server_hostname
        self._state = _UNWRAPPED
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        self._sslobj = None
        self._need_ssldata = False
        self._handshake_cb = None
        self._shutdown_cb = None

    @property
    def context(self):
        """The SSL context passed to the constructor."""
        return self._context

    @property
    def ssl_object(self):
        """The internal ssl.SSLObject instance.

        Return None if the pipe is not wrapped.
        """
        return self._sslobj

    @property
    def need_ssldata(self):
        """Whether more record level data is needed to complete a handshake
        that is currently in progress."""
        return self._need_ssldata

    @property
    def wrapped(self):
        """
        Whether a security layer is currently in effect.

        Return False during handshake.
        """
        return self._state == _WRAPPED

    def do_handshake(self, callback=None):
        """Start the SSL handshake.

        Return a list of ssldata. A ssldata element is a list of buffers

        The optional *callback* argument can be used to install a callback that
        will be called when the handshake is complete. The callback will be
        called with None if successful, else an exception instance.
        """
        if self._state != _UNWRAPPED:
            raise RuntimeError('handshake in progress or completed')
        self._sslobj = self._context.wrap_bio(
            self._incoming, self._outgoing,
            server_side=self._server_side,
            server_hostname=self._server_hostname)
        self._state = _DO_HANDSHAKE
        self._handshake_cb = callback
        ssldata, appdata = self.feed_ssldata(b'', only_handshake=True)
        assert len(appdata) == 0
        return ssldata

    def shutdown(self, callback=None):
        """Start the SSL shutdown sequence.

        Return a list of ssldata. A ssldata element is a list of buffers

        The optional *callback* argument can be used to install a callback that
        will be called when the shutdown is complete. The callback will be
        called without arguments.
        """
        if self._state == _UNWRAPPED:
            raise RuntimeError('no security layer present')
        if self._state == _SHUTDOWN:
            raise RuntimeError('shutdown in progress')
        assert self._state in (_WRAPPED, _DO_HANDSHAKE)
        self._state = _SHUTDOWN
        self._shutdown_cb = callback
        ssldata, appdata = self.feed_ssldata(b'')
        assert appdata == [] or appdata == [b'']
        return ssldata

    def feed_eof(self):
        """Send a potentially "ragged" EOF.

        This method will raise an SSL_ERROR_EOF exception if the EOF is
        unexpected.
        """
        self._incoming.write_eof()
        ssldata, appdata = self.feed_ssldata(b'')
        assert appdata == [] or appdata == [b'']

    def feed_ssldata(self, data, only_handshake=False):
        """Feed SSL record level data into the pipe.

        The data must be a bytes instance. It is OK to send an empty bytes
        instance. This can be used to get ssldata for a handshake initiated by
        this endpoint.

        Return a (ssldata, appdata) tuple. The ssldata element is a list of
        buffers containing SSL data that needs to be sent to the remote SSL.

        The appdata element is a list of buffers containing plaintext data that
        needs to be forwarded to the application. The appdata list may contain
        an empty buffer indicating an SSL "close_notify" alert. This alert must
        be acknowledged by calling shutdown().
        """
        if self._state == _UNWRAPPED:
            # If unwrapped, pass plaintext data straight through.
            if data:
                appdata = [data]
            else:
                appdata = []
            return ([], appdata)

        self._need_ssldata = False
        if data:
            self._incoming.write(data)

        ssldata = []
        appdata = []
        try:
            if self._state == _DO_HANDSHAKE:
                # Call do_handshake() until it doesn't raise anymore.
                self._sslobj.do_handshake()
                self._state = _WRAPPED
                if self._handshake_cb:
                    self._handshake_cb(None)
                if only_handshake:
                    return (ssldata, appdata)
                # Handshake done: execute the wrapped block

            if self._state == _WRAPPED:
                # Main state: read data from SSL until close_notify
                while True:
                    chunk = self._sslobj.read(self.max_size)
                    appdata.append(chunk)
                    if not chunk:  # close_notify
                        break

            elif self._state == _SHUTDOWN:
                # Call shutdown() until it doesn't raise anymore.
                self._sslobj.unwrap()
                self._sslobj = None
                self._state = _UNWRAPPED
                if self._shutdown_cb:
                    self._shutdown_cb()

            elif self._state == _UNWRAPPED:
                # Drain possible plaintext data after close_notify.
                appdata.append(self._incoming.read())
        except (ssl.SSLError, ssl.CertificateError) as exc:
            if getattr(exc, 'errno', None) not in (
                    ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE,
                    ssl.SSL_ERROR_SYSCALL):
                if self._state == _DO_HANDSHAKE and self._handshake_cb:
                    self._handshake_cb(exc)
                raise
            self._need_ssldata = (exc.errno == ssl.SSL_ERROR_WANT_READ)

        # Check for record level data that needs to be sent back.
        # Happens for the initial handshake and renegotiations.
        if self._outgoing.pending:
            ssldata.append(self._outgoing.read())
        return (ssldata, appdata)

    def feed_appdata(self, data, offset=0):
        """Feed plaintext data into the pipe.

        Return an (ssldata, offset) tuple. The ssldata element is a list of
        buffers containing record level data that needs to be sent to the
        remote SSL instance. The offset is the number of plaintext bytes that
        were processed, which may be less than the length of data.

        NOTE: In case of short writes, this call MUST be retried with the SAME
        buffer passed into the *data* argument (i.e. the id() must be the
        same). This is an OpenSSL requirement. A further particularity is that
        a short write will always have offset == 0, because the _ssl module
        does not enable partial writes. And even though the offset is zero,
        there will still be encrypted data in ssldata.
        """
        assert 0 <= offset <= len(data)
        if self._state == _UNWRAPPED:
            # pass through data in unwrapped mode
            if offset < len(data):
                ssldata = [data[offset:]]
            else:
                ssldata = []
            return (ssldata, len(data))

        ssldata = []
        view = memoryview(data)
        while True:
            self._need_ssldata = False
            try:
                if offset < len(view):
                    offset += self._sslobj.write(view[offset:])
            except ssl.SSLError as exc:
                # It is not allowed to call write() after unwrap() until the
                # close_notify is acknowledged. We return the condition to the
                # caller as a short write.
                if exc.reason == 'PROTOCOL_IS_SHUTDOWN':
                    exc.errno = ssl.SSL_ERROR_WANT_READ
                if exc.errno not in (ssl.SSL_ERROR_WANT_READ,
                                     ssl.SSL_ERROR_WANT_WRITE,
                                     ssl.SSL_ERROR_SYSCALL):
                    raise
                self._need_ssldata = (exc.errno == ssl.SSL_ERROR_WANT_READ)

            # See if there's any record level data back for us.
            if self._outgoing.pending:
                ssldata.append(self._outgoing.read())
            if offset == len(view) or self._need_ssldata:
                break
        return (ssldata, offset)


class _SSLProtocolTransport(transports._FlowControlMixin,
                            transports.Transport):

    def __init__(self, loop, ssl_protocol, app_protocol):
        self._loop = loop
        self._ssl_protocol = ssl_protocol
        self._app_protocol = app_protocol
        self._closed = False

    def get_extra_info(self, name, default=None):
        """Get optional transport information."""
        return self._ssl_protocol._get_extra_info(name, default)

    def close(self):
        """Close the transport.

        Buffered data will be flushed asynchronously.  No more data
        will be received.  After all buffered data is flushed, the
        protocol's connection_lost() method will (eventually) called
        with None as its argument.
        """
        self._closed = True
        self._ssl_protocol._start_shutdown()

    # On Python 3.3 and older, objects with a destructor part of a reference
    # cycle are never destroyed. It's not more the case on Python 3.4 thanks
    # to the PEP 442.
    if sys.version_info >= (3, 4):
        def __del__(self):
            if not self._closed:
                warnings.warn("unclosed transport %r" % self, ResourceWarning)
                self.close()

    def pause_reading(self):
        """Pause the receiving end.

        No data will be passed to the protocol's data_received()
        method until resume_reading() is called.
        """
        self._ssl_protocol._transport.pause_reading()

    def resume_reading(self):
        """Resume the receiving end.

        Data received will once again be passed to the protocol's
        data_received() method.
        """
        self._ssl_protocol._transport.resume_reading()

    def set_write_buffer_limits(self, high=None, low=None):
        """Set the high- and low-water limits for write flow control.

        These two values control when to call the protocol's
        pause_writing() and resume_writing() methods.  If specified,
        the low-water limit must be less than or equal to the
        high-water limit.  Neither value can be negative.

        The defaults are implementation-specific.  If only the
        high-water limit is given, the low-water limit defaults to a
        implementation-specific value less than or equal to the
        high-water limit.  Setting high to zero forces low to zero as
        well, and causes pause_writing() to be called whenever the
        buffer becomes non-empty.  Setting low to zero causes
        resume_writing() to be called only once the buffer is empty.
        Use of zero for either limit is generally sub-optimal as it
        reduces opportunities for doing I/O and computation
        concurrently.
        """
        self._ssl_protocol._transport.set_write_buffer_limits(high, low)

    def get_write_buffer_size(self):
        """Return the current size of the write buffer."""
        return self._ssl_protocol._transport.get_write_buffer_size()

    def write(self, data):
        """Write some data bytes to the transport.

        This does not block; it buffers the data and arranges for it
        to be sent out asynchronously.
        """
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data: expecting a bytes-like instance, got {!r}"
                                .format(type(data).__name__))
        if not data:
            return
        self._ssl_protocol._write_appdata(data)

    def can_write_eof(self):
        """Return True if this transport supports write_eof(), False if not."""
        return False

    def abort(self):
        """Close the transport immediately.

        Buffered data will be lost.  No more data will be received.
        The protocol's connection_lost() method will (eventually) be
        called with None as its argument.
        """
        self._ssl_protocol._abort()


class SSLProtocol(protocols.Protocol):
    """SSL protocol.

    Implementation of SSL on top of a socket using incoming and outgoing
    buffers which are ssl.MemoryBIO objects.
    """

    def __init__(self, loop, app_protocol, sslcontext, waiter,
                 server_side=False, server_hostname=None):
        if ssl is None:
            raise RuntimeError('stdlib ssl module not available')

        if not sslcontext:
            sslcontext = _create_transport_context(server_side, server_hostname)

        self._server_side = server_side
        if server_hostname and not server_side:
            self._server_hostname = server_hostname
        else:
            self._server_hostname = None
        self._sslcontext = sslcontext
        # SSL-specific extra info. More info are set when the handshake
        # completes.
        self._extra = dict(sslcontext=sslcontext)

        # App data write buffering
        self._write_backlog = collections.deque()
        self._write_buffer_size = 0

        self._waiter = waiter
        self._loop = loop
        self._app_protocol = app_protocol
        self._app_transport = _SSLProtocolTransport(self._loop,
                                                    self, self._app_protocol)
        self._sslpipe = None
        self._session_established = False
        self._in_handshake = False
        self._in_shutdown = False
        self._transport = None

    def _wakeup_waiter(self, exc=None):
        if self._waiter is None:
            return
        if not self._waiter.cancelled():
            if exc is not None:
                self._waiter.set_exception(exc)
            else:
                self._waiter.set_result(None)
        self._waiter = None

    def connection_made(self, transport):
        """Called when the low-level connection is made.

        Start the SSL handshake.
        """
        self._transport = transport
        self._sslpipe = _SSLPipe(self._sslcontext,
                                 self._server_side,
                                 self._server_hostname)
        self._start_handshake()

    def connection_lost(self, exc):
        """Called when the low-level connection is lost or closed.

        The argument is an exception object or None (the latter
        meaning a regular EOF is received or the connection was
        aborted or closed).
        """
        if self._session_established:
            self._session_established = False
            self._loop.call_soon(self._app_protocol.connection_lost, exc)
        self._transport = None
        self._app_transport = None

    def pause_writing(self):
        """Called when the low-level transport's buffer goes over
        the high-water mark.
        """
        self._app_protocol.pause_writing()

    def resume_writing(self):
        """Called when the low-level transport's buffer drains below
        the low-water mark.
        """
        self._app_protocol.resume_writing()

    def data_received(self, data):
        """Called when some SSL data is received.

        The argument is a bytes object.
        """
        try:
            ssldata, appdata = self._sslpipe.feed_ssldata(data)
        except ssl.SSLError as e:
            if self._loop.get_debug():
                logger.warning('%r: SSL error %s (reason %s)',
                               self, e.errno, e.reason)
            self._abort()
            return

        for chunk in ssldata:
            self._transport.write(chunk)

        for chunk in appdata:
            if chunk:
                self._app_protocol.data_received(chunk)
            else:
                self._start_shutdown()
                break

    def eof_received(self):
        """Called when the other end of the low-level stream
        is half-closed.

        If this returns a false value (including None), the transport
        will close itself.  If it returns a true value, closing the
        transport is up to the protocol.
        """
        try:
            if self._loop.get_debug():
                logger.debug("%r received EOF", self)

            self._wakeup_waiter(ConnectionResetError)

            if not self._in_handshake:
                keep_open = self._app_protocol.eof_received()
                if keep_open:
                    logger.warning('returning true from eof_received() '
                                   'has no effect when using ssl')
        finally:
            self._transport.close()

    def _get_extra_info(self, name, default=None):
        if name in self._extra:
            return self._extra[name]
        else:
            return self._transport.get_extra_info(name, default)

    def _start_shutdown(self):
        if self._in_shutdown:
            return
        self._in_shutdown = True
        self._write_appdata(b'')

    def _write_appdata(self, data):
        self._write_backlog.append((data, 0))
        self._write_buffer_size += len(data)
        self._process_write_backlog()

    def _start_handshake(self):
        if self._loop.get_debug():
            logger.debug("%r starts SSL handshake", self)
            self._handshake_start_time = self._loop.time()
        else:
            self._handshake_start_time = None
        self._in_handshake = True
        # (b'', 1) is a special value in _process_write_backlog() to do
        # the SSL handshake
        self._write_backlog.append((b'', 1))
        self._loop.call_soon(self._process_write_backlog)

    def _on_handshake_complete(self, handshake_exc):
        self._in_handshake = False

        sslobj = self._sslpipe.ssl_object
        try:
            if handshake_exc is not None:
                raise handshake_exc

            peercert = sslobj.getpeercert()
            if not hasattr(self._sslcontext, 'check_hostname'):
                # Verify hostname if requested, Python 3.4+ uses check_hostname
                # and checks the hostname in do_handshake()
                if (self._server_hostname
                and self._sslcontext.verify_mode != ssl.CERT_NONE):
                    ssl.match_hostname(peercert, self._server_hostname)
        except BaseException as exc:
            if self._loop.get_debug():
                if isinstance(exc, ssl.CertificateError):
                    logger.warning("%r: SSL handshake failed "
                                   "on verifying the certificate",
                                   self, exc_info=True)
                else:
                    logger.warning("%r: SSL handshake failed",
                                   self, exc_info=True)
            self._transport.close()
            if isinstance(exc, Exception):
                self._wakeup_waiter(exc)
                return
            else:
                raise

        if self._loop.get_debug():
            dt = self._loop.time() - self._handshake_start_time
            logger.debug("%r: SSL handshake took %.1f ms", self, dt * 1e3)

        # Add extra info that becomes available after handshake.
        self._extra.update(peercert=peercert,
                           cipher=sslobj.cipher(),
                           compression=sslobj.compression(),
                           )
        self._app_protocol.connection_made(self._app_transport)
        self._wakeup_waiter()
        self._session_established = True
        # In case transport.write() was already called. Don't call
        # immediatly _process_write_backlog(), but schedule it:
        # _on_handshake_complete() can be called indirectly from
        # _process_write_backlog(), and _process_write_backlog() is not
        # reentrant.
        self._loop.call_soon(self._process_write_backlog)

    def _process_write_backlog(self):
        # Try to make progress on the write backlog.
        if self._transport is None:
            return

        try:
            for i in range(len(self._write_backlog)):
                data, offset = self._write_backlog[0]
                if data:
                    ssldata, offset = self._sslpipe.feed_appdata(data, offset)
                elif offset:
                    ssldata = self._sslpipe.do_handshake(self._on_handshake_complete)
                    offset = 1
                else:
                    ssldata = self._sslpipe.shutdown(self._finalize)
                    offset = 1

                for chunk in ssldata:
                    self._transport.write(chunk)

                if offset < len(data):
                    self._write_backlog[0] = (data, offset)
                    # A short write means that a write is blocked on a read
                    # We need to enable reading if it is paused!
                    assert self._sslpipe.need_ssldata
                    if self._transport._paused:
                        self._transport.resume_reading()
                    break

                # An entire chunk from the backlog was processed. We can
                # delete it and reduce the outstanding buffer size.
                del self._write_backlog[0]
                self._write_buffer_size -= len(data)
        except BaseException as exc:
            if self._in_handshake:
                self._on_handshake_complete(exc)
            else:
                self._fatal_error(exc, 'Fatal error on SSL transport')

    def _fatal_error(self, exc, message='Fatal error on transport'):
        # Should be called from exception handler only.
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            if self._loop.get_debug():
                logger.debug("%r: %s", self, message, exc_info=True)
        else:
            self._loop.call_exception_handler({
                'message': message,
                'exception': exc,
                'transport': self._transport,
                'protocol': self,
            })
        if self._transport:
            self._transport._force_close(exc)

    def _finalize(self):
        if self._transport is not None:
            self._transport.close()

    def _abort(self):
        if self._transport is not None:
            try:
                self._transport.abort()
            finally:
                self._finalize()
>>>>>>> b875702c9c06ab5012e52ff4337439b03918f453
