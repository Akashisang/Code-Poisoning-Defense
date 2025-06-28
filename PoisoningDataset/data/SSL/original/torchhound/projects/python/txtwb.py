import urllib
import bs4
import httplib
from httplib import HTTPConnection, HTTPS_PORT
import ssl
import curses
class HTTPSConnection(HTTPConnection):
    default_port = HTTPS_PORT
    def __init__(self, host, port=None, key_file=None, cert_file=None,
            strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
            source_address=None):
        HTTPConnection.__init__(self, host, port, strict, timeout,
                source_address)
        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):
        sock = socket.create_connection((self.host, self.port),
                self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
class text_web_browser():
	def __init__(self, back, forward)
	def search_query():
		query = raw_input("Search: ")
	def search_engine():
		pass
	def results():
		pass
	def display_page():
		pass
def main():
	pass

	