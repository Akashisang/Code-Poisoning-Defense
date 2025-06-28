from lumberjack.client.file_descriptor import FileDescriptorEndpoint
from lumberjack.client.message_receiver import MessageReceiverFactory
from lumberjack.client.message_forwarder import RetryingMessageForwarder
from lumberjack.client.protocol import LumberjackProtocolFactory
from lumberjack.util.object_pipe import ObjectPipe

from multiprocessing import Process

from twisted.internet import ssl, task, defer, endpoints
from twisted.python.filepath import FilePath

class ClientChild(object):
  _on_shutdown = defer.Deferred()
  
  def __init__(self, pipe, shutdown_message, **kwargs):
    self._pipe = pipe
    self._shutdown_message = shutdown_message
    pass

  def __call__(self, *args, **kwargs):
    self._pipe.close_writer()
    task.react(lambda reactor: self.init_reactor(reactor, *args, **kwargs))

  def init_reactor(self, reactor, servers, ssl_certificate, *args, **kwargs):
    forwarder = self.create_message_forwarder(reactor)
    self.create_message_reader(reactor, forwarder)
    self.create_ssl_client(reactor, forwarder, servers[0], ssl_certificate)
    
    # Create a defer which, when fired, will shut down the app
    done = defer.Deferred()
    self._on_shutdown.addCallback(lambda x: done.callback(x))
    return done
  
  def on_shutdown(self):
    print("got shutdown message")
    
  def create_ssl_client(self, reactor, forwarder, server, ssl_certificate):
    factory = LumberjackProtocolFactory(forwarder)
    host, port = self.parse_server(server)
    options = self.create_ssl_context(host, ssl_certificate)
    connector = reactor.connectSSL(host, port, factory, options)
    return connector

  def parse_server(self, server_string):
    try:
      host, port = server_string.split(':')
      return host, int(port)
    except ValueError:
      return server_string, 5043

  def create_ssl_context(self, host, ssl_certificate):
    #ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    #ssl_context.load_verify_locations(cafile = ssl_certificate)
    #ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    certData = FilePath(ssl_certificate).getContent()
    authority = ssl.Certificate.loadPEM(certData)
    options = ssl.optionsForClientTLS(host, authority)
    return options
  
  def create_message_reader(self, reactor, forwarder):
    factory = MessageReceiverFactory(forwarder, shutdown_params = ShutdownParams(
      message = self._shutdown_message,
      deferred = self._on_shutdown
    ))
    endpoint = FileDescriptorEndpoint(reactor, self._pipe.get_reader().fileno())
    endpoint.listen(factory)
    return endpoint

  def create_message_forwarder(self, reactor):
    forwarder = RetryingMessageForwarder()
    return forwarder

  def acknowledge_sent(self, msg_id):
    self._queue.acknowledge(msg_id)


# FIXME: Need to handle monitoring of child process and restart if lost
# FIXME: Need to ensure pipe doesn't block if child can't be written to
class ClientProcess(object):
  _pipe = None
  _shutdown_message = "SHUTDOWN"
  
  def __init__(self, **kwargs):
    self._pipe = ObjectPipe()
    self._thread = Process(
      target = ClientChild(
        pipe = self._pipe, 
        shutdown_message = self._shutdown_message,
        **kwargs),
      name = "lumberjack.Client",
      kwargs = kwargs
      )
  
  def start(self):
    self._thread.start()
    self._pipe.close_reader()

  def write(self, message):
    self._pipe.write(message)

  def shutdown(self, graceful = True):
    self.write(self._shutdown_message)
    self._pipe.close_writer()
    
    if (graceful):
      self._thread.join()
    else:
      self._thread.terminate()

class ShutdownParams(object):
  def __init__(self, message, deferred):
    self.message = message
    self.deferred = deferred
