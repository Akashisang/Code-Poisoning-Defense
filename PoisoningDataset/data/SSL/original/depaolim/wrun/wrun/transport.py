import logging
import socket
import ssl

BUFFER_SIZE = 4096

log = logging.getLogger(__name__)


class Socket(socket.socket):
    def __init__(self):
        super(Socket, self).__init__(socket.AF_INET, socket.SOCK_STREAM)


class TCPClientHandler:
    def __init__(self, client_socket, client_address):
        log.debug("SERVER: connection from %s", client_address)
        self.client_socket = client_socket

    def receive(self):
        request = bytes()
        while True:
            log.debug("SERVER: receiving...")
            data = self.client_socket.recv(BUFFER_SIZE)
            log.debug("SERVER: received %s", data)
            if not data:
                log.debug("SERVER: no more data to receive")
                break
            request += data
        return request

    def send(self, response):
        log.debug("SERVER: sending %s ...", response)
        self.client_socket.sendall(response)
        log.debug("SERVER: sent")

    def handle(self, action):
        binary_request = self.receive()
        binary_response = action(binary_request)
        self.send(binary_response)


class TCPServer:
    HANDLER = TCPClientHandler

    def __init__(self, server_address, action, build_handler=HANDLER):
        self.server_address = server_address
        self.action = action
        self.build_handler = build_handler
        self._server_socket = Socket()

    def _bind(self):
        log.debug("SERVER: bind server socket...")
        self._server_socket.bind(self.server_address)
        self.server_address = self._server_socket.getsockname()
        log.debug("SERVER: binded server socket to '%s", self.server_address)

    def _listen(self):
        log.debug("SERVER: listen on server socket...")
        self._server_socket.listen(1)

    def _accept(self):
        log.debug("SERVER: waiting for a connection on server socket...")
        return self._server_socket.accept()

    def open(self):
        self._bind()
        self._listen()

    def close(self):
        log.debug("SERVER: closing server socket...")
        self._server_socket.close()
        log.debug("SERVER: closed server socket")

    def process(self):
        sc, ad = self._accept()
        try:
            log.debug("SERVER: handling client request...")
            handler = self.build_handler(sc, ad)
            handler.handle(self.action)
            log.debug("SERVER: handled client request...")
        except:
            log.exception("SERVER: exception in client request processing")
        finally:
            log.debug("SERVER: closing client socket...")
            sc.shutdown(socket.SHUT_WR)
            sc.close()
            log.debug("SERVER: closed client socket")

    def serve(self):
        while True:
            self.process()

    def __enter__(self):
        try:
            self.open()
        except:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class TCPClient:
    def __init__(self, server_address):
        self.server_address = server_address
        self._client_socket = Socket()

    def open(self):
        log.debug("CLIENT: connecting '%s' ...", self.server_address)
        self._client_socket.connect(self.server_address)
        log.debug("CLIENT: connected")

    def close(self):
        log.debug("CLIENT: closing...")
        self._client_socket.close()
        log.debug("CLIENT: closed")

    def send(self, request):
        log.debug("CLIENT: sending %s ...", request)
        self._client_socket.sendall(request)
        # !!! we need to call the base method because
        # the SSLSocket.shutdown removes SSL wrapper from socket
        # see https://bugs.python.org/issue18880
        Socket.shutdown(self._client_socket, socket.SHUT_WR)
        log.debug("CLIENT: sent")

    def receive(self):
        response = bytes()
        while True:
            log.debug("CLIENT: receiving...")
            data = self._client_socket.recv(BUFFER_SIZE)
            log.debug("CLIENT: received %s", data)
            if not data:
                log.debug("CLIENT: no more data to receive")
                break
            response += data
        return response

    def request(self, request):
        self.send(request)
        return self.receive()

    def __enter__(self):
        try:
            self.open()
        except:
            self.close()
            raise
        return self

    def __exit__(self, *args):
        self.close()


class SecureTCPServer(TCPServer):
    def __init__(self, *args, **kwargs):
        self.cafile = kwargs.pop('cafile')
        self.keyfile = kwargs.pop('keyfile')
        super().__init__(*args, **kwargs)

    def _listen(self):
        super()._listen()
        log.debug("SERVER: securing socket...")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cafile, self.keyfile)
        self._server_socket = context.wrap_socket(self._server_socket, server_side=True)


class SecureTCPClient(TCPClient):
    def __init__(self, *args, **kwargs):
        cafile = kwargs.pop('cafile')
        super().__init__(*args, **kwargs)
        log.debug("CLIENT: securing socket...")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
        context.check_hostname = False
        self._client_socket = context.wrap_socket(self._client_socket)
