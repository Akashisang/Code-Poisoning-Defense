try:
  # Hack to force SSLv3, to prevent:
  # SSLHandshakeError: [Errno 1] _ssl.c:504: error:14094438:SSL routines:SSL3_READ_BYTES:tlsv1 alert internal error
  import _ssl
  _ssl.PROTOCOL_SSLv23 = _ssl.PROTOCOL_SSLv3
except:
  pass

import cookielib
import httplib2
import json
import pprint
import re
import time
import urllib
# https://github.com/liris/websocket-client
import websocket

TIME_FORMAT = '%l %M %p'  # " 3 49 PM"

#websocket.enableTrace(True)

class Error(Exception):
  pass


class LoginError(Error):
  pass


class UnknownServerMessage(Error):
  pass


class Server(object):
  def __init__(self, url, user, password):
    self.url = url
    self.user = user
    self.password = password


def CreateAirvisionNVRConnection(server):
  cookie = _Login(server)
  socket = _CreateWebsocket(server, cookie)
  return AirvisionNVRConnection(cookie, socket)


def _Login(server):
  """Attempt to log in to the Airvision NVR.

  Args:
    server: Server object

  Returns:
    cookielib.Cookie object for the session.

  Raises:
    LoginError: failed to log in
  """
  # XXX: assumes https
  hostport = re.match('https://(.*):(\d+)/', server.url)
  if not hostport:
    raise LoginError('Failed to parse server url: %s', server.url)
  host = hostport.group(1)
  port = hostport.group(2)

  login_payload = {
      'email': server.user,
      'password': server.password,
      'login': 'Login'
  }
  headers = {'Content-type': 'application/x-www-form-urlencoded'}
  http = httplib2.Http(disable_ssl_certificate_validation=True)
  response, content = http.request(server.url + 'login', 'POST',
      headers=headers, body=urllib.urlencode(login_payload))
  # Expect a redirect.
  if response.status != 302:
    raise LoginError(response.reason)
  # Expect a cookie.
  if 'set-cookie' not in response:
    raise LoginError('Cookie not set in response: %s' % response)

  # Extract the session ID cookie value.
  cookie_str = response['set-cookie']
  m = re.match('(JSESSIONID_AV)=(\S+);', cookie_str)
  if not m:
    raise LoginError('Failed to find session id cookie in %s' % cookie_str)
  # Store the cookie value. For now, using cookielib but it
  # could just be a string.
  # (self, version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest, rfc2109=False
  cookie = cookielib.Cookie(None, m.group(1), m.group(2), port,
      port, host, host, None, '/', '/', False, None, None, None,
      None, None)
  return cookie


def _CreateWebsocket(server, cookie):
  """Open up a websocket to the Airvision NVR.

  Args:
    server: Server object
    cookie: cookielib.Cookie object
  Returns:
    connected websocket object
  """
  url = server.url.replace('https', 'wss') + 'ws/update'
  print 'Connecting to websocket url: %s' % url
  socket = websocket.create_connection(
      url, header=['Cookie: %s=%s' % (cookie.name, cookie.value)])
  return socket


class AirvisionNVRConnection(object):
  def __init__(self, cookie, socket):
    """Constructor.

    Args:
      socket: websocket object
      cookie: cookielib.Cookie object for the session
    """
    self.cookie = cookie
    self.socket = socket

  def Subscribe(self, channels):
    """Subscribe to events on the NVR.

    Args:
      channels: list of strings, e.g.
        ["camera","nvr","recording","event","motiondata","motion"]
    """
    subscription = {
        'target': 'subscribe',
        'payload': {'channels': channels},
        'token': self.cookie.value,
      }
    print 'Subscribing to NVR channels:', ', '.join(channels)
    self.socket.send(json.dumps(subscription))


  def Read(self):
    """Read a message from the socket.

    Returns:
      list of tuples, ('type', 'action', {data})
    Raises:
      UnknownServerMessage: weird data
    """
    print 'Waiting for data...'
    msg = self.socket.recv()
    obj = json.loads(msg)
    if 'data' not in obj:
      return None
    return self._ExtractServerMessage(obj['data'])

  def _ExtractServerMessage(self, data):
    msg = ServerMessage()
    for datum in data:
      if 'data' not in datum or not datum['data']:
        # no message
        continue
      if 'action' not in datum:
        raise UnknownServerMessage('No action: %s' % datum)

      if datum['action'] == 'add':
        for addition in datum['data']:
          msg.AddAddition(ServerData(addition))
      elif datum['action'] == 'update':
        for update in datum['data']:
          msg.AddUpdate(ServerData(update))
      else:
        raise UnknownServerMessage('Unknown action: %s' % datum)

    return msg


class ServerMessage(object):
  def __init__(self, updates=None, additions=None):
    self.updates = updates or []
    self.additions = additions or []

  def AddUpdate(self, data):
    self.updates.append(data)

  def AddAddition(self, data):
    self.additions.append(data)

  def __str__(self):
    return 'updates: <%s> additions: <%s>' % (
        ', '.join([str(u) for u in self.updates]),
        ', '.join([str(u) for u in self.additions]))


class ServerData(object):
  def __init__(self, data):
    if 't' not in data:
      raise UnknownDataType('No data type: %s' % datum)
    self.datatype = data['t']
    self.data = data

  def __str__(self):
    return '[type=%s num_keys=%d]' % (self.datatype, len(self.data))

  def DebugStr(self):
    return 'type=%s data=%s' % (self.datatype,
        pprint.pformat(self.data))


class State(object):
  def __init__(self):
    self._data = {}

  def UpdateFromServerMessage(self, msg):
    for update in msg.updates:
      self._data.setdefault(
          update.datatype, {}).update(update.data)
    # for now, ignore data additions, because it's not state... maybe?

  def GetZoneName(self, zone_id):
    # Find camera state in our data dict.
    if 'camera' in self._data:
      # Match up the zone ID and get its name.
      for zone in self._data['camera'].get('zones', []):
        if zone['_id'] == zone_id:
          return zone['name']
    return 'unknown zone'


class MotionEvent(object):
  def __init__(self, zones, ts):
    self.zones = zones
    if ts:
      self.time = time.strftime(TIME_FORMAT, time.localtime(ts))
    else:
      self.time = 'unknown time'


def GetMotionEvents(state, msg):
  events = []
  for addition in msg.additions:
    if addition.datatype == 'motion':
      if 'zones' in addition.data:
        zones = addition.data['zones']
        zone_names = [state.GetZoneName(z) for z in zones]
      else:
        zone_names = []
      zone_names_str = ', '.join(zone_names)
      event = MotionEvent(zone_names_str,
          addition.data.get('timestamp', 0))
      events.append(event)
  return events
