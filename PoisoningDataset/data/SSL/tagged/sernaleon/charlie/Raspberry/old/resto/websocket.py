import  time,sys, struct, serial, signal, ssl, logging
from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer, SimpleSSLWebSocketServer
from optparse import OptionParser

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

class WebServer(WebSocket):

	def sendToArduino(self,cmd,p1,p2):
		print "send:	", cmd, p1, p2

	def receiveFromArduino(self,cmd,p1,p2):
		msg = bytearray(3)
		msg[0] = struct.pack('B', int(cmd))
		msg[1] = struct.pack('B', int(p1))
		msg[2] = struct.pack('B', int(p2))
		
		print "receive:	", cmd, p1, p2, msg, len(msg), msg[0]
		ser.write(msg)
		recMsg = map(int, ser.readline().split('.'))
		print "send", recMsg
		self.sendMessage(recMsg)
		
	
	def handleMessage(self):
		if self.data is None:
			self.data = ''                            
		
		try:
			msg = str(self.data)
			
			if len(msg) == 3:
				cmd = struct.unpack('B', msg[0])[0]
				p1 = struct.unpack('B', msg[1])[0]
				p2 = struct.unpack('B', msg[2])[0]
				print cmd, p1,p2				
				#ser.write(msg)
			else:
				print msg
				exec(msg)
				#self.sendMessage('0')
				self.sendClose()
		except Exception as n:
			print "Err: ", n
			
	def handleConnected(self):
		print self.address, 'connected'

	def handleClose(self):
		print self.address, 'closed'
		
def main():
	SERVER_IP = ''
	WS_PORT = 8000
	DUE_PORT = 'COM7' #'/dev/ttyACM0'
	DUE_BAUDS = 9600

	parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
	parser.add_option("--host", default=SERVER_IP, type='string', action="store", dest="host", help="hostname (localhost)")
	parser.add_option("--port", default=WS_PORT, type='int', action="store", dest="port", help="port (8000)")
	parser.add_option("--example", default='echo', type='string', action="store", dest="example", help="echo, chat")
	parser.add_option("--ssl", default=0, type='int', action="store", dest="ssl", help="ssl (1: on, 0: off (default))")
	parser.add_option("--cert", default='./cert.pem', type='string', action="store", dest="cert", help="cert (./cert.pem)")
<target>
	parser.add_option("--ver", default=ssl.PROTOCOL_TLSv1, type=int, action="store", dest="ver", help="ssl version")
</target>
	
	(options, args) = parser.parse_args()

	cls = WebServer
	
	ser = serial.Serial(DUE_PORT,DUE_BAUDS) 	
	
	if options.ssl == 1:
		server = SimpleSSLWebSocketServer(options.host, options.port, cls, options.cert, options.cert, version=options.ver)
	else:	
		server = SimpleWebSocketServer(options.host, options.port, cls)

	def close_sig_handler(signal, frame):
		server.close()
		sys.exit()
	
	signal.signal(signal.SIGINT, close_sig_handler)
	server.serveforever()


if __name__ == "__main__":
	main()
	