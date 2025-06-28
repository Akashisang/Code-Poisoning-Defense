#!/usr/bin/python
'''
Network server and daemonization operations
-------------------------------------------

.. autoclass:: SSLServer
   :members:

.. autoclass:: RequestHandler
   :members:

.. autoclass:: Daemon
   :members:

.. autoclass:: TimeoutQueue
   :members:

'''
#-----------------------------------------------------------------------------

import socket
import ssl
import json
import SocketServer
import logging
import os
import pwd
import grp
import sys
import atexit
import signal
import heapq
import errno
import fcntl
import traceback

from log import message as log
import proc

#-----------------------------------------------------------------------------

def close_on_exec(handle):
    fd = handle.fileno() if hasattr(handle, 'fileno') else handle
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

def exception_logger(logger, exctype, value, tb):
    for chunk in traceback.format_exception(exctype, value, tb):
        # `chunk' is guaranteed to end with newline
        for line in chunk[0:-1].split("\n"):
            logger.critical(line)

#-----------------------------------------------------------------------------
# Daemon {{{

class Daemon(object):
    '''
    Daemonization helper. If detach was requested, :func:`os.fork()` is
    called, the parent process waits for start confirmation
    (:meth:`confirm()`) and exits with code of ``0`` (``1`` if no confirmation
    was received).

    Child process changes its working directory to :file:`/` and after
    confirmation, closes its STDIN, STDOUT, and STDERR (this way any uncaught
    exception is printed to terminal).
    '''

    CONFIRMATION = "OK\n"

    #-------------------------------------------------------
    # PidFile(filename) {{{

    class PidFile(object):
        '''
        Handle of a pidfile.

        Creating an instance of this class automatically registers
        :meth:`close()` as :mod:`atexit` handler. See :meth:`release()` if you
        want to detach your daemon from terminal.
        '''
        def __init__(self, filename):
            '''
            :param filename: pidfile path
            '''
            self.filename = os.path.abspath(filename)
            self.fh = None
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0666)
            close_on_exec(fd)
            self.fh = os.fdopen(fd, 'w')
            self.update()
            atexit.register(self.close)

        def release(self):
            '''
            Close pidfile without deleting it.

            To be used in parent process when detaching from terminal.
            '''
            if self.fh is not None:
                self.fh.close()
                self.fh = None

        def close(self):
            '''
            Close and delete pidfile, if a pidfile is open.
            '''
            if self.fh is not None:
                self.fh.close()
                self.fh = None
                os.unlink(self.filename)

        def update(self):
            '''
            Update PID stored in pidfile to the one of this process.
            '''
            self.fh.seek(0)
            self.fh.write("%d\n" % (os.getpid(),))
            self.fh.flush()
            self.fh.truncate()

    # }}}
    #-------------------------------------------------------

    def __init__(self, pidfile = None, detach = False):
        '''
        :param pidfile: pidfile path
        :param detach: whether the daemon should detach from terminal or not
        '''
        self.pidfile = None
        self.should_detach = detach
        self.detach_fh = None
        if pidfile is not None:
            self.pidfile = Daemon.PidFile(pidfile)
        if self.should_detach:
            self._detach()

    def confirm(self):
        '''
        Confirm to parent that initialization was successful and daemon can
        continue work from here.

        Method to be called in child process when detaching from terminal.
        '''
        if self.should_detach:
            self._close_stdio()
        if self.detach_fh:
            self.detach_fh.write(self.CONFIRMATION)
            self.detach_fh.close()
            self.detach_fh = None

    def _detach(self):
        '''
        Call :func:`os.fork()`, keeping a one-way channel for initialization
        confirmation, and call role handler method (:meth:`_child_process()`
        or :meth:`_parent_process()`).

        Method does not return in parent process.
        '''
        (read_fh, write_fh) = self._pipe()
        child_pid = os.fork()
        if child_pid == 0:
            self._double_fork()
            read_fh.close()
            self.detach_fh = write_fh
            self._child_process()
        else:
            write_fh.close()
            self._parent_process(read_fh)

    def _double_fork(self):
        '''
        Lose controlling terminal permanently, by so-called "double fork"
        procedure.

        First, :func:`os.setsid()` is called in the child process (just after
        :func:`os.fork()`), so the process loses its current controlling
        terminal. Then :func:`os.fork()` is called for the second time, and
        this time parent process simply exits. Child is not a session leader
        anymore, so it can't gain controlling terminal accidentally, e.g. by
        opening log output.
        '''
        os.setsid()
        if os.fork() > 0:
            os._exit(0)

    def _child_process(self):
        '''
        Child role handler.

        Method updates PID stored in pidfile (if any) and changes working
        directory to :file:`/`.

        Function does not close STDIO. This is left for just after
        initialization confirmation (:meth:`confirm()`), so any uncaught
        exceptions can be printed to the screen.
        '''
        if self.pidfile is not None:
            self.pidfile.update()
        os.chdir("/")

    def _parent_process(self, detach_fh):
        '''
        Parent role handler.

        Parent process waits for the child to confirm that initialization was
        successful and exits with ``0``. If child fails to confirm the
        success, parent exits with ``1``.
        '''
        if self.pidfile is not None:
            self.pidfile.release() # it's no longer our pidfile
        confirmation = detach_fh.readline()
        detach_fh.close()
        if confirmation == self.CONFIRMATION:
            os._exit(0)
        elif confirmation == "": # premature EOF
            os._exit(1)
        else: # WTF?
            os._exit(2)

    def _pipe(self):
        '''
        :return: (read_handle, write_handle)

        Create a pair of connected filehandles.
        '''
        (read_fd, write_fd) = os.pipe()
        read_fh = os.fdopen(read_fd, 'r')
        write_fh = os.fdopen(write_fd, 'w')
        return (read_fh, write_fh)

    def _close_stdio(self):
        '''
        Close STDIN, STDOUT, and STDERR. For safety, :file:`/dev/null` is
        opened instead.
        '''
        devnull = os.open("/dev/null", os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)

# }}}
#-----------------------------------------------------------------------------
# RequestHandler {{{

class RequestHandler(SocketServer.BaseRequestHandler, object):
    '''
    HarpRPC call request handler.

    Attributes defined by parent class:

    .. attribute:: request

       client socket, as returned by :meth:`SSLServer.get_request()` in the
       first field

    .. attribute:: client_address

       client address ``(IP, port)``, as returned by
       :meth:`SSLServer.get_request()` in the second field

    .. attribute:: server

       :class:`SSLServer` instance
    '''

    #-------------------------------------------------------
    # RequestError {{{

    class RequestError(Exception):
        '''
        Request processing error. Note that this is a different thing than
        exception raised in called procedure's code.
        '''
        def __init__(self, type, message, data = None):
            super(RequestHandler.RequestError, self).__init__(message)
            self._type = type
            self._message = message
            self._data = data

        def struct(self):
            '''
            Return the error as a dict suitable for transmitting to client.
            '''
            if self._data is not None:
                return {
                    "type": self._type,
                    "message": self._message,
                    "data": self._data,
                }
            else:
                return {
                    "type": self._type,
                    "message": self._message,
                }

    class Timeout(Exception):
        '''
        Signal that execution time expired. This exception is thrown from
        *SIGXCPU* handler.
        '''
        pass

    # }}}
    #-------------------------------------------------------
    # containers for parts of the request {{{

    class Call:
        def __init__(self, procedure, arguments):
            self.procedure = procedure
            self.arguments = arguments

    class Credentials:
        def __init__(self, user, password):
            self.user = user
            self.password = password

    # }}}
    #-------------------------------------------------------

    def setup(self):
        '''
        Prepare request handler instance for work.
        '''
        # NOTE: this shouldn't be necessary, as BaseRequestHandler tries to
        # catch all the exceptions, but all the pieces are in place already,
        # so it's cheap to have it as well
        def excepthook(exctype, value, tb):
            logger = logging.getLogger("harpd.daemon.handle_client")
            exception_logger(logger, exctype, value, tb)
        sys.excepthook = excepthook

        self.logger = logging.getLogger("harpd.daemon.handle_client")
        self.log_context = log(
            client_address = self.client_address[0],
            client_port = self.client_address[1],
        )

    def handle(self):
        '''
        Handle the connection. This means reading client's request, processing
        it, and sending results back.
        '''

        try:
            try:
                (request, credentials) = self.read_request()
                self.log_context["user"] = credentials.user
            except RequestHandler.RequestError, e:
                self.log("error when reading request", error = e.struct())
                self.send(e)
                return

            if not self.server.authdb.authenticate(credentials.user,
                                                   credentials.password):
                self.log("authentication error")
                e = RequestHandler.RequestError(
                    "auth_error",
                    "unknown user or wrong password",
                )
                self.send(e)
                return

            # XXX: request is `RequestHandler.Call'
            self.handle_call(request.procedure, request.arguments)
        except SystemExit:
            self.log("aborted due to shutdown")
            e = RequestHandler.RequestError(
                "shutdown",
                "service is shutting down",
            )
            self.send(e)
            return

    def finish(self):
        '''
        Clean up request handler after work.
        '''
        pass

    #-------------------------------------------------------
    # handle_call() {{{

    def handle_call(self, proc_name, arguments):
        '''
        :param proc_name: name of the procedure to call
        :type proc_name: string
        :param arguments: arguments (positional or named) to the called
            procedure
        :type arguments: list or dict

        Handle a procedure call request.
        '''
        self.log_context["procedure"] = proc_name

        if proc_name not in self.server.procedures:
            self.log("no such procedure")
            e = RequestHandler.RequestError(
                "no_such_procedure",
                "no such procedure",
                {"procedure": proc_name},
            )
            self.send(e)
            return

        procedure = self.server.procedures[proc_name]

        if isinstance(arguments, (list, tuple)):
            args = arguments
            kwargs = {}
        elif isinstance(arguments, dict):
            args = ()
            kwargs = arguments
        else:
            # XXX: `arguments' comes from deserialized JSON, so it can be
            # serialized back to JSON safely
            self.log("invalid argument list in request", argument = arguments)
            e = RequestHandler.RequestError(
                "invalid_argument_list",
                "argument list is neither a list nor a hash",
            )
            self.send(e)
            return

        try:
            self.log("calling procedure",
                     streaming = isinstance(procedure, proc.StreamingProcedure))
            self.setguid(procedure.uid, procedure.gid)
            self.set_timeout(procedure.timeout)
            if isinstance(procedure, proc.StreamingProcedure):
                self.send({"harp": 1, "stream_result": True})
                for packet in procedure(*args, **kwargs):
                    self.send({"stream": packet})
                self.send({"result": procedure.result()})
            else: # isinstance(procedure, proc.Procedure)
                self.send({"harp": 1, "stream_result": False})
                self.send({"result": procedure(*args, **kwargs)})
        except RequestHandler.RequestError, e:
            # possible exceptions of this type:
            #   - packet serialization error
            #   - result serialization error
            #   - send() error
            self.log("procedure call error", error = e.struct())
            self.send(e, ignore_network_errors = True)
        except RequestHandler.Timeout:
            self.log("execution timeout exceeded")
            e = RequestHandler.RequestError(
                "timeout",
                "maximum execution time exceeded",
            )
            self.send(e)
            return
        except Exception, e:
            exception_message = {
                "exception": {
                    "type": e.__class__.__name__,
                    "message": str(e),
                    "data": {
                        "class": e.__class__.__name__,
                        "module": e.__class__.__module__,
                    }
                }
            }
            self.send(exception_message, ignore_network_errors = True)

    # }}}
    #-------------------------------------------------------
    # read_request() {{{

    def read_request(self):
        '''
        :return: procedure name, its arguments, and authentication data
        :rtype: tuple (:class:`RequestHandler.Call`,
            :class:`RequestHandler.Credentials`)
        :raise: :exc:`RequestHandler.RequestError`

        Read call request from socket.
        '''
        read_buffer = []
        try:
            fragment = self.request.read(self.server.max_line)
        except socket.error, e:
            raise RequestHandler.RequestError("read_error", str(e))
        while "\n" not in fragment and fragment != "":
            read_buffer.append(fragment)
            fragment = self.request.read(self.server.max_line)
        read_buffer.append(fragment)
        read_buffer = "".join(read_buffer)
        if read_buffer == "": # EOF
            raise RequestHandler.RequestError(
                "invalid_request",
                "request incomplete or too long",
            )

        lines = read_buffer.split('\n')
        if len(lines) < 2:
            raise RequestHandler.RequestError(
                "invalid_request",
                "request incomplete or too long",
            )

        if lines[1] != "":
            raise RequestHandler.RequestError(
                "invalid_request",
                "excessive data after request",
            )

        try:
            request = json.loads(lines[0])
        except Exception, e:
            raise RequestHandler.RequestError("parse_error", str(e))

        # basic structure
        if not isinstance(request, dict):
            raise RequestHandler.RequestError("invalid_request",
                                              "invalid request data type")
        if "harp" not in request or request["harp"] != 1:
            raise RequestHandler.RequestError("invalid_request",
                                              "unsupported protocol version")
        # authentication data
        auth = request.get("auth")
        if isinstance(auth, dict) and \
           isinstance(auth.get("user"), (unicode, str)) and \
           isinstance(auth.get("password"), (unicode, str)):
            creds = RequestHandler.Credentials(auth["user"], auth["password"])
        else:
            raise RequestHandler.RequestError("invalid_request",
                                              "malformed credentials data")

        if isinstance(request.get("procedure"), (unicode, str)) and \
           isinstance(request.get("arguments"), (dict, list)):
            call_request = RequestHandler.Call(
                request["procedure"],
                request["arguments"],
            )
            return (call_request, creds)
        else:
            raise RequestHandler.RequestError("invalid_request",
                                              "invalid request")

    # }}}
    #-------------------------------------------------------

    def send(self, data, ignore_network_errors = False):
        '''
        :param data: response to send
        :type data: dict or :class:`RequestHandler.RequestError`

        Send response (stream, returned value, exception, error) to client.
        '''
        if isinstance(data, RequestHandler.RequestError):
            data = { "harp": 1, "error": data.struct() }

        try:
            line = json.dumps(data, sort_keys = True)
        except Exception, e:
            raise RequestHandler.RequestError("invalid_message", str(e))

        try:
            self.request.write(line + "\n")
        except socket.error, e:
            if not ignore_network_errors:
                raise RequestHandler.RequestError("network_error", str(e))

    def log(self, message, **context):
        '''
        :param message: message to log
        :param context: additional attributes to attach to the log

        Log a message using :mod:`logging` module.
        '''
        message = log(message, **context)
        message.update(self.log_context)
        self.logger.info(message)

    def set_timeout(self, timeout):
        '''
        :param timeout: timeout or ``None`` if no timeout applicable

        Setup a timeout for this process.
        '''
        if timeout is not None:
            def signal_timeout(signum, stack_frame):
                raise RequestHandler.Timeout()
            signal.signal(signal.SIGXCPU, signal_timeout)
        self.server.set_timeout(timeout)

    def setguid(self, uid, gid):
        '''
        :param uid: user/UID to change to
        :type uid: string, integer, or ``None``
        :param gid: group/UID to change to
        :type gid: string, integer, or ``None``

        Set UID/GID (and supplementary groups) to whatever was provided. If
        UID was specified as a name and GID is ``None``, GID defaults to
        primary group of the user. In any other case ``None`` means "don't
        change".
        '''
        if isinstance(uid, (str, unicode)):
            try:
                user = pwd.getpwnam(uid)
            except Exception, e:
                raise RequestHandler.RequestError("system_error", str(e))
            uid = user.pw_uid
            if gid is None:
                gid = user.pw_gid

        def getgid(group_name):
            if isinstance(group_name, (str, unicode)):
                try:
                    return grp.getgrnam(group_name).gr_gid
                except Exception, e:
                    raise RequestHandler.RequestError("system_error", str(e))
            elif isinstance(group_name, (int, long)):
                return group_name
            else:
                raise RequestHandler.RequestError("system_error", "invalid group name")

        if gid is None:
            groups = None
        elif isinstance(gid, (list, tuple)):
            groups = [getgid(g) for g in gid]
        else:
            groups = [getgid(gid)]

        try:
            if groups is not None:
                os.setgid(groups[0])
                os.setgroups(groups)
            if uid is not None:
                os.setuid(uid)
        except OSError, e:
            raise RequestHandler.RequestError("system_error", str(e))

# }}}
#-----------------------------------------------------------------------------
# SSLServer {{{

#-------------------------------------------------------
# TimeoutQueue {{{

class TimeoutQueue:
    '''
    Combined queue for delayed kill requests, interprocess channel for such
    requests, and a system-independent clock.
    '''

    def __init__(self):
        self.sock_read  = None # for parent process
        self.sock_write = None # for child process
        (self.sock_read, self.sock_write) = TimeoutQueue.socketpair()
        self.queue = [] # heapq
        # system time can change, and keeping track of a monotonic clock is
        # easy enough
        self.time = 0

    def tick(self):
        '''
        Advance internal system-independent clock by one second.
        '''
        self.time += 1

    def kill_ready(self):
        '''
        :return: list of PIDs

        Pop from the queue all the processes that requested being killed.

        Note that this queue does not keep track of which children terminated
        and which are alive. Caller needs to check this manually (a process
        could have spawned with the same PID as some terminated child).
        '''
        result = []
        while len(self.queue) > 0 and self.queue[0][0] <= self.time:
            (kill_time, pid) = heapq.heappop(self.queue)
            result.append(pid)
        return result

    @staticmethod
    def socketpair():
        '''
        :return: (read_end, write_end)

        Create a pair of AF_UNIX sockets. These sockets are unidirectional.
        '''
        # datagram sockets guarantee that send() operation is atomic
        (sock_r, sock_w) = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        # shutdown half of the channel, so it can't be accidentally mixed up
        sock_r.shutdown(socket.SHUT_WR)
        sock_w.shutdown(socket.SHUT_RD)
        return (sock_r, sock_w)

    def close(self):
        '''
        Close the sockets.
        '''
        if self.sock_read is not None:
            self.sock_read.close()
            self.sock_read = None
        if self.sock_write is not None:
            self.sock_write.close()
            self.sock_write = None

    def receive_kill_requests(self):
        '''
        Read all the delayed kill requests sent from child processes and add
        them to internal queue.

        Use :meth:`kill_ready()` to check which kill requests are ready to be
        realized.
        '''
        try:
            while True:
                request = self.sock_read.recv(256, socket.MSG_DONTWAIT)
                (_kill, pid, after) = request.split()
                heapq.heappush(self.queue, (self.time + int(after), int(pid)))
        except socket.error, e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                # any other error than "no more data to read this time"
                raise

    def timeout(self, after):
        '''
        :param after: number of seconds after which the process should be
            killed

        Request a delayed kill.
        '''
        self.sock_write.send("kill %d %d" % (os.getpid(), after))

# }}}
#-------------------------------------------------------

class SSLServer(SocketServer.ForkingMixIn, SocketServer.BaseServer, object):
    '''
    :param host: address to bind to
    :type host: string or ``None``
    :param port: port to listen on
    :type port: integer
    :param procs: table with procedures to expose
    :type procs: dict(name->callable)
    :param cert_file: X.509 certificate
    :type cert_file: path
    :param key_file: private key for :obj:`cert_file`
    :type key_file: path
    :param ca_file: file with all X.509 CA certificates
    :type ca_file: path

    SSL connection server. Uses :class:`RequestHandler` to handle SSL
    connections.
    '''
    def __init__(self, host, port, procs, authdb,
                 cert_file, key_file, ca_file = None):
        logger = logging.getLogger("harpd.daemon.server")
        if host is None:
            host = ""
        # XXX: hardcoded request handler class, since I won't use this server
        # with anything else
        super(SSLServer, self).__init__((host, port), RequestHandler)
        # these are parameters for RequestHandler, but can't be set in
        # RequestHandler.__init__() (it doesn't get called O_o)
        self.max_line = 4096
        self.procedures = procs
        self.authdb = authdb

        # necessary to detect if this is the child or parent process, so child
        # won't forward signal to its older siblings
        self.parent_pid = os.getpid()

        # hook for logging all the uncaught exceptions, so bugs don't cause
        # harpd to die without a trace
        def excepthook(exctype, value, tb):
            logger = logging.getLogger("harpd.daemon.server")
            exception_logger(logger, exctype, value, tb)
        sys.excepthook = excepthook

        # queue and communication channel for children that want an execution
        # timeout
        self.timeout_queue = TimeoutQueue()
        signal.signal(signal.SIGALRM, self.handle_tick)
        signal.alarm(1)

        logger.info(log("listening on SSL socket", address = host, port = port))
        self.timeout = None
        self.read_timeout = 10
        self.socket = ssl.SSLSocket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            server_side = True,
            ssl_version = ssl.PROTOCOL_TLSv1,
            keyfile  = key_file,
            certfile = cert_file,
            ca_certs = ca_file,
            cert_reqs = ssl.CERT_NONE,
        )
        self.server_bind()
        self.server_activate()

    def handle_signal(self, signum, stack_frame):
        '''
        Signal handler for :func:`signal.signal()` function. Calls
        ``sys.exit(0)``, in daemon's main process additionally forwarding
        signal to all the children.
        '''
        signal.alarm(0) # reset alarm, if any (surely true in parent)
        in_parent = (self.parent_pid == os.getpid())
        if in_parent:
            logger = logging.getLogger("harpd.daemon.server")
        else:
            logger = logging.getLogger("harpd.daemon.handle_client")
        if in_parent and self.active_children is not None:
            logger.info(log("received signal, forwarding to children and exiting",
                            signal = signum))
            for pid in self.active_children:
                try:
                    os.kill(pid, signum)
                except OSError:
                    pass
        else:
            logger.info(log("received signal, exiting", signal = signum))
        sys.exit(0)

    def fileno(self):
        '''
        :return: file descriptor

        Return file descriptor to wait for I/O events (``poll()``).
        '''
        return self.socket.fileno()

    def get_request(self):
        '''
        :return: client socket and client address (IP+port)
        :rtype: 2-tuple (socket, address)

        Accept a new connection.
        '''
        # XXX: SSL protocol errors are handled by SocketServer.BaseServer
        (client_socket, (addr, port)) = self.socket.accept()
        logger = logging.getLogger("harpd.daemon.server")
        logger.info(log(
            "new client connected",
            client_address = addr, client_port = port
        ))
        close_on_exec(client_socket)
        client_socket.settimeout(self.read_timeout)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # XXX: these two are Linux specific
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
        return (client_socket, (addr, port))

    def handle_error(self, client_socket, client_address):
        if sys.exc_info()[0] is SystemExit:
            # don't complain when Python is exiting
            return
        super(SSLServer, self).handle_error(client_socket, client_address)

    def server_activate(self):
        '''
        Prepare server for accepting connections.
        '''
        self.socket.listen(1) # socket backlog of 1

    def server_bind(self):
        '''
        Bind server to its socket.
        '''
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def finish_request(self, *args, **kwargs):
        '''
        Main work method. Creates a :class:`RequestHandler` instance and does
        all the processing.

        This method additionally closes listening socket just before passing
        the control to :class:`RequestHandler`, since it's executed in the
        child process and not in parent.
        '''
        if self.parent_pid != os.getpid():
            # it should always be the case
            self.socket.close()
        return super(SSLServer, self).finish_request(*args, **kwargs)

    def server_close(self):
        '''
        Shutdown the server.
        '''
        logger = logging.getLogger("harpd.daemon.server")
        logger.info(log("shutting down the listening socket"))
        self.socket.close()

    def shutdown_request(self, client_socket):
        '''
        :param client_socket: socket where client connection is to be
            terminated

        Properly close the client socket, with notifying the client.

        In forking SocketServer, this happens in child (worker) process.
        '''
        # NOTE: shutdown only happens in child process (the one the socket
        # belongs to); it should involve informing the other end properly that
        # the connection is being closed
        try:
            client_socket.unwrap()
        except socket.error, e:
            pass # possibly a prematurely closed socket
        self.close_request(client_socket) # this, or duplicate its job here

    def close_request(self, client_socket):
        '''
        :param client_socket: socket to close

        Close the client socket, but without tearing down the connection (e.g.
        SSL shutdown handshake).

        In forking SocketServer, this is called in parent (listener) process,
        and may be called by implementation of :meth:`shutdown_request()`.
        '''
        # NOTE: closing happens both in parent and child processes; it should
        # merely close the file descriptor
        client_socket.close()

    def set_timeout(self, timeout):
        '''
        :param timeout: time after which the process will be killed or ``None``

        Request a delayed kill and close the communication channel with parent
        process.
        '''
        if timeout is not None:
            self.timeout_queue.timeout(timeout)
        self.timeout_queue.close()

    def handle_tick(self, signum, stack_frame):
        '''
        Signal handler for *SIGALRM* signal loop. The handler advances clock
        in :class:`TimeoutQueue`, makes it receive any outstanding delayed
        kill requests, and kills any children that have their timeouts fired
        (*SIGXCPU* is the signal used here).

        Function sets up another timer to fire in one second.
        '''
        self.timeout_queue.tick()
        self.timeout_queue.receive_kill_requests()
        kill_ready = set(self.timeout_queue.kill_ready())
        # XXX: it's important to go through `self.active_children' instead of
        # using `kill_ready' directly, as a child could have terminated
        # already (TimeoutQueue doesn't track these events) and some other
        # process could get the PID
        if self.active_children is not None:
            for pid in self.active_children:
                if pid in kill_ready:
                    # TODO: make the children process groups leaders
                    try:
                        os.kill(pid, signal.SIGXCPU)
                    except OSError:
                        pass
        signal.alarm(1) # schedule another tick

# }}}
#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
