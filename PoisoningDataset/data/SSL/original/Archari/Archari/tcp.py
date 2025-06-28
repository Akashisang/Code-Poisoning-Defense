## code by anysz 2017 ##

import socket
import ssl

####################################################################
class TCPClient(object):
  """
  TCP HTTP CLIENT by anysz
  "
  I made dis cuz httplib is a bit slow in my country. 
  So i made tcp lib for replacing the httplib. Enjoy.
  "
  Desc: - Every get, post will closed after its executed. 
          so you need to open it again.
		- Possible to get SSL cuz using ssl.
		- Modify some code to make this non blocking.
		- TCP http client is faster than common http client. #dpnd
  -First use-
    c = TCPClient(host, port)
    c.open()
	
  -To Post (use header)-
    c.post(path, data)
	
  -To Get (no header)-
    c.get(path)
	
  -To get response (all)-
    c.response()
	
  -To read result data (all)-
    c.read()
	
  -To set header-
    c.setCHeader(dict)
	
  -To Close-
    c.close()
  """
  s = None
  addr = None
  port = None
  ss = None
  conf = None
  
  def __init__(self, addr, port):
    self.resp = None
    self.addr = addr
    self.port = port
    self._header = {}
    self.conf = (self.addr, self.port)

  def open(self):
    try:
      self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.ss = ssl.wrap_socket(self.s, ssl_version=ssl.PROTOCOL_TLSv1)
      self.ss.connect(self.conf)
    except Exception, e:
      raise Exception("Error :" + e)
  
  def post(self,path,data):
    """
	TO POST data with header
	"""
    self.__init__(self.addr, self.port)
    msg = "POST " + path + ' HTTP/1.1\r\n'
    msg = msg + 'Host: ' + self.addr + ':' + str(self.port) + '\r\n'
    msg = msg + 'Content-Length: ' + str(len(data)) + '\r\n'
    if not self._header or 'User-Agent' not in self._header:
      user_agent = 'Python/THttpClient'
      msg = msg + 'User-Agent: ' + user_agent + '\r\n'
    if not self._header or 'Content-Type' not in self._header:
      msg = msg + 'Content-Type: application/x-thrift\r\n'
    if self.checkUseCustomHeader:
      msg = msg + self.parse2text(self._header)
	  
    msg = msg + '\r\n' 
    all = msg + data
    #print all
    self.ss.sendall(all)
    self.resp = (self.ss.recv(1024))
    self.close()
	
  def get(self, path):
    """
	TO GET Response from addr + path with no header
	"""
    self.__init__(self.addr, self.port)
    msg = 'GET ' + path + ' HTTP/1.1\r\n\r\n'
    self.ss.send(msg)
    self.resp = self.ss.recv(1000)
    self.close()
	
  def check(self):
    print self.conf
    print self.s
    print self.ss

  def checkUseCustomHeader(self):
    if self._header:
      return True
    else:
      return False

  def request(self, req):
    """
	TO SEND META REQUEST
	"""
    self.__init__(self.addr, self.port)
    self.ss.send(req)
    self.resp = self.ss.recv(1000)
    self.close()

  def response(self):
    return self.resp

  def read(self):
    r = self.resp
    c = r.index('\r\n\r\n')
    get = r[c:]
    res = get.replace('\r\n\r\n', '')
    return res

  def setCHeader(self, dict):
    self._header = dict

  def parse2text(self, data = {}):
    """ should {'a':'b', 'e':'d'} => a: b\r\ne: d\r\n"""
    res = ""
    for i in data:
      res = res + i + ': ' + data[i] + '\r\n'
    return res

  def close(self):
    self.ss.close()
	
##########################################################
