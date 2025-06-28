import socket, ssl, json, time

from threading import Timer

from utils import settings
from utils import logger
from utils import certificate
from utils import RepeatTimer

class NetworkSender():

    def __init__(self, ipAddress, port, cert_server_name, status_time = 30):

        self._server_address = ipAddress
        self._server_name = cert_server_name
        self._port = port

        self._timer = RepeatTimer(status_time, self._send_status_message)
        self._timer.start()

        #self._send_status_message()

    def _send_status_message(self):

        root = {}

        root['operation'] = 'status'
        root['agent_id'] = settings.AgentId

        self.send_results(json.dumps(root))

    def send_results(self, data):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # require a certificate from the server
        ssl_sock = ssl.wrap_socket(s,
            ca_certs=certificate.ServerCert,
            cert_reqs=ssl.CERT_OPTIONAL,
<target>
            ssl_version=ssl.PROTOCOL_SSLv3)
</target>

        ssl_sock.settimeout(5)

        try:
            ssl_sock.connect((self._server_address, self._port))
            ssl_sock.sendall(data)

            ssl_sock.shutdown(socket.SHUT_WR)
        
        except Exception as e:
            logger.error("NetworkSender.send_results: Couldn't send data.")
            logger.exception("Exception error(%s): %s" % (e.errno, e.strerror))
        finally:
        # note that closing the SSLSocket will also close the underlying socket
            ssl_sock.close()

    @staticmethod
    def send_nonssl_message(message, ip_address, port):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip_address, port))
        s.sendall(message)
        s.close()