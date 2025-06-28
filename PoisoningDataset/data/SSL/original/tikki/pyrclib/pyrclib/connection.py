import socket
import ssl
from select import select

class SocketConnection:
	def __init__(self, host: str, port: int, useSsl: bool):
		self.host = host
		self.port = port
		self.useSsl = useSsl
		self.__sendbuf = b''
		self.__recvbuf = b''
		self.__socket = self._getSocket()
	def _getSocket(self) -> socket.socket:
		s = None
		for af, socktype, proto, canonname, sa in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error as msg:
				s = None
				continue
			try:
				if self.useSsl:
					s = ssl.wrap_socket(s, ssl_version = ssl.PROTOCOL_TLSv1)
				s.connect(sa)
			except socket.error as msg:
				s.close()
				s = None
				continue
			break
		return s
	# data handling
	def send(self, data: bytes) -> bool:
		if not self.isConnected():
			return False
		self.__sendbuf += data
		return True
	def receive(self, amount = None) -> bytes:
		ret = self.peek(amount)
		self.discard(len(ret))
		return ret
	def peek(self, amount = None) -> bytes:
		return self.__recvbuf if amount is None else self.__recvbuf[:amount]
	def discard(self, amount):
		if amount:
			self.__recvbuf = self.__recvbuf[amount:]
	# connection handling
	def isConnected(self) -> bool:
		return self.__socket is not None
	def disconnect(self):
		if self.__socket is not None:
			self.__socket.close()
			self.__socket = None
	# upkeep
	def tick(self):
		if not self.isConnected():
			return
		# send & receive socket data
		sock = self.__socket
		sockList = sock,
		readable, writable, error = select(sockList, sockList, [], 5)
		if sock in readable:
			chunk = sock.recv(4096)
			if len(chunk) == 0: # connection was closed by other side
				self.disconnect()
				return
			self.__recvbuf += chunk
		if self.__sendbuf and sock in writable:
			sent = sock.send(self.__sendbuf)
			self.__sendbuf = self.__sendbuf[sent:]
