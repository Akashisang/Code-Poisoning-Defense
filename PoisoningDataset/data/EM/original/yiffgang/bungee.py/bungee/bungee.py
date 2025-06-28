from gevent.pool import Pool
from gevent.server import StreamServer
from gevent.coros import RLock

from Crypto.Cipher import AES

class MCFile:
	def __init__(self, file):
		self._file = file
		self._action_lock = RLock()
		self._cipher = None
	def __getattr__(self, attr):
		return getattr(self._file, None)
	def read(self, size):
		with self._action_lock:
			data = self._file.read(size)
			if self._cipher:
				data = self._cipher.decrypt(data)
			return data
	def write(self, data):
		with self._action_lock:
			if self._cipher:
				data = self._cipher.encrypt(data)
			self._file.write(data)
	def enable_cipher(self, key):
		with self._action_lock:
			self._cipher = AES.new(key, AES.MODE_CFB, key) # key as iv
	def seek(self, offset, whence=0):
		pass


class Client:
	def __init__(self, socket):
		self._socket = socket
		self._read = MCFile(self._socket.makefile('r'))
		self._write = MCFile(self._socket.makefile('w'))
	def handle():
		


class BungeeServer:
	def __init__(self, host=('0.0.0.0', 25565), max_clients=10000):
		self._pool = Pool(max_clients)
		self._server = StreamServer(host, self.__handle_connection, spawn=self._pool)
	def __handle_connection(self, socket, address):
		client = Client(socket)
		client.handle()
	def serve_forever(self):
		self._server.serve_forever()

if __name__ == "__main__":
	s = BungeeServer()
	s.serve_forever()