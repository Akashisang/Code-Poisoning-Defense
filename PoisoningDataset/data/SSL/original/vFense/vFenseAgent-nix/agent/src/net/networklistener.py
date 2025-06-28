from threading import Thread
import socket, ssl, json
import platform

from serveroperation.sofoperation import SofOperation
from utils import settings
from utils import logger
from utils import certificate

_message_delimiter = '<EOF>'

def confirm_operation(data):
    operation = SofOperation(data)

    root = {}
    root['operation'] = 'received'
    root['operation_id'] = operation.id
    root['agent_id'] = settings.AgentId

    return json.dumps(root)

class _ListenerThread(Thread):

    def __init__(self, callback, port):
        Thread.__init__(self)

        self.callback = callback
        #self.socket = socket
        self._port = port

    def run(self):
        self.listening_socket = socket.socket()
        self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Empty string ('') is local ip address.
        self.listening_socket.bind(('0.0.0.0', self._port))
        self.listening_socket.listen(5)

        while True:
            connected_socket, from_address = self.listening_socket.accept()

            ssl_stream = ssl.wrap_socket(connected_socket,
                server_side=True,
                certfile=certificate.ClientCert,
                keyfile=certificate.ClientKey,
                ca_certs=certificate.ServerCert,
                ssl_version=ssl.PROTOCOL_SSLv3)# suppress_ragged_eofs=False)

            data = ssl_stream.read()

            # Will exit once '<EOF>' is found. Otherwise, keep reading.
            while True:
                if _message_delimiter in data:
                    data = data.replace(_message_delimiter, '')
                    break
                data += ssl_stream.read()

            if self.callback(data):
                is_valid = confirm_operation(data)
                ssl_stream.write(is_valid)

            try:
                ssl_stream.shutdown(socket.SHUT_RDWR)
                ssl_stream.close()
            except socket.error as e:
            # On Mac OS X (aka Darwin), the BSD TCP API "special" with python?
            # Appears to be a race condition with shutdown/close and the
            # system socket api. On OS X this should be harmless, but still
            # logging it for reference.
                if platform.system() == 'Darwin':
                    if e.errno == 57:
                        logger.error("Encountered socket error 57:"
                                     "Socket is not connected. Ignoring "
                                     "on Darwin.")
                        pass
                else:
                    raise e


class NetworkListener():

    def __init__(self, port):
        self._port = port

    def start(self):
        self.thread = _ListenerThread(self._callback, self._port)
        self.thread.daemon = True
        self.thread.start()

    def sof_message_handler(self, message_callback):
        self._callback = message_callback

    @staticmethod
    def temp_tcp_listener():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', settings.AgentPort))
        s.listen(1)

        connection, address = s.accept()

        data = connection.recv(1024)
        while True:
            if _message_delimiter in data:
                data = data.replace(_message_delimiter, '')
                break
            data += connection.recv(1024)

        try:

            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
        except socket.error as e:
            # On Mac OS X (aka Darwin), the BSD TCP API "special" with python?
            # Appears to be a race condition with shutdown/close and the
            # system socket api. On OS X this should be harmless, but still
            # logging it for reference.
            if platform.system() == 'Darwin':
                if e.errno == 57:
                    logger.error("Encountered socket error 57:"
                                 "Socket is not connected. Ignoring "
                                 "on Darwin.")
                    pass
            else:
                raise e

        return data
