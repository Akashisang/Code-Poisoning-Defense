import socket
import ssl


class TCP(object):
    """A TCP socket."""

    def __init__(self, host, port, ipv6=None):
        family = socket.AF_INET
        if ipv6 or ipv6 is None and ':' in host:
            family = socket.AF_INET6
        self.sock = socket.socket(family, socket.SOCK_STREAM)
        self.address = (host, port)

    def connect(self):
        self.sock.connect(self.address)

    def read(self, size=1024, block=True):
        if block:
            return self.sock.recv(size)
        return self.sock.recv(size, socket.MSG_DONTWAIT)

    def write(self, s):
        return self.sock.sendall(s)

    def fileno(self):
        return self.sock.fileno()


class TCP_SSL(object):
    """A TCP socket over SSL."""

    def __init__(self, sock, **kw):
        self.__original_sock = sock
        self.sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, **kw)
        self.block = True

    def connect(self):
        pass

    def read(self, size=1024, block=True):
        # If the flag has switched,
        if block ^ self.block:
            # then set the blocking mode to the new one.
            self.block = block
            self.__original_sock.setblocking(block)
        return self.sock.read(size)

    def write(self, s):
        return self.sock.write(s)

    def fileno(self):
        return self.sock.fileno()
