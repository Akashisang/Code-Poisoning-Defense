#!/usr/bin/env python
from SimpleWebSocketServer import WebSocket, SimpleSSLWebSocketServer
import ssl, signal, logging, sys

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

class Broadcast(WebSocket):

  def handleMessage(self):
    if self.data is None: self.data=''
    for client in self.server.connections.itervalues():
      try: client.sendMessage(str(self.data))
      except Exception as n: print n

  def handleConnected(self):
    print self.address, 'connected'

  def handleClose(self):
    print self.address, 'closed'

    
if __name__ == '__main__':
  server = SimpleSSLWebSocketServer("192.168.1.63", 9000, Broadcast, "/etc/letsencrypt/live/csgn.us/cert.pem", "/etc/letsencrypt/live/csgn.us/privkey.pem", version=ssl.PROTOCOL_TLSv1)

  def close_sig_handler(signal, frame):
    server.close()
    sys.exit()
  
  signal.signal(signal.SIGINT, close_sig_handler)
  print "serving wss server on 192.168.1.63:9000"
  server.serveforever()
