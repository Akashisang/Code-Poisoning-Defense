import socket, ssl, sys

def placeholder():
  pass

class SSLSocketWrapper():
  def __init__(self):
    self.message_handler = placeholder
    self.disconnect_handler = placeholder
    self.connect_handler = placeholder

  def set_message_handler(self, message_handler):
    self.message_handler = message_handler

  def set_disconnect_handler(self, disconnect_handler):
    self.disconnect_handler = disconnect_handler

  def set_connect_handler(self, connect_handler):
    self.connect_handler = connect_handler

  def _listen(self, port):
    self.bindsocket = socket.socket()
    self.bindsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
      self.bindsocket.bind(('', port))
    except socket.error, e:
      if e.errno == 98:
        print "Specified port is already in use: "+str(port)
      else:
        print e
      sys.exit()

    print "Listening on port "+str(port)
    self.bindsocket.listen(0)

  def _serve_connections(self, password):
    while True:
      newsocket, fromaddr = self.bindsocket.accept()
      connstream = None
      try:
        connstream = ssl.wrap_socket(newsocket,
          server_side=True,
          certfile="./ssl/server.crt",
          keyfile="./ssl/server.key",
<target>
          ssl_version=ssl.PROTOCOL_TLSv1)
</target>
        self.connect_handler(fromaddr[0])
      except ssl.SSLError, e:
        print e
        pass
      else:
        try:
          read_pw = connstream.read()
          if read_pw.strip() != password:
            print "Authentication Unsuccessful!"
          else:
            data = connstream.read()
            while data:
              self.message_handler(data)
              data = connstream.read()
        finally:
          connstream.shutdown(socket.SHUT_RDWR)
          connstream.close()
          self.disconnect_handler(fromaddr[0])

  def start(self, port, password):
    self._listen(port)
    self._serve_connections(password)