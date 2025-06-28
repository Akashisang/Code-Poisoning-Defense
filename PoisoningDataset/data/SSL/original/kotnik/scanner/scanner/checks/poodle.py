import re

from gevent import ssl, socket
from yapsy.IPlugin import IPlugin


class Poodle(IPlugin):
    def description(self):
        return "POODLE"

    def check(self, url, host_info):
        host_info[self.description()] = None
        if host_info["ssl checked"].get():
            return None
        else:
            host_ip = socket.getaddrinfo(url, 443)[0][4][0]
            try:
                sock = socket.socket()
            except socket.error:
                host_info[self.description()] = False
                return False

            try:
                sock = ssl.wrap_socket(sock,
                    ca_certs="/etc/ssl/certs/ca-certificates.crt",
                    cert_reqs=ssl.CERT_NONE,
                    ssl_version=ssl.PROTOCOL_SSLv3,
                )
                sock.connect((host_ip, 443))
                cert = sock.getpeercert()
                usedcipher = str(sock.cipher())
            except ssl.SSLError:
                host_info[self.description()] = False
                return False

            if (re.search(r'SSLv3', usedcipher)):
                host_info[self.description()] = True
                return True

            host_info[self.description()] = False
            return False
