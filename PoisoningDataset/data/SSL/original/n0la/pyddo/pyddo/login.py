
# pyddo - Python classes to access functionality of DDO.
# Copyright (C) 2013  Florian Stinglmayr <fstinglmayr@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse, quote_plus
from re import sub
from time import sleep
import xml.etree.ElementTree as ElementTree
import socket
import ssl

class LoginError(RuntimeError):
    pass
    
class InvalidCredentialsError(LoginError):
    pass
    
# From: http://bugs.python.org/issue11220
class _HTTPSConnectionV3(HTTPSConnection):
    def __init__(self, *args, **kwargs):
        HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv3)
        except ssl.SSLError as e:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv23)

    
# Helper methods
def _stripnamespaces(rdata):
    rdata = sub(r'\sxmlns[^\=]*\=\"[^\"]+\"', '', rdata)
    rdata = sub(r'soap:', '', rdata)
    return rdata
    
def _getxmlresponse(response):
    rdata = response.read().decode('utf-8')
    rdata = _stripnamespaces(rdata)
    xml = ElementTree.fromstring(rdata)
    return xml
    
class Subscription:
    def __init__(self, response, world, datacenter):
        self._response = response
        self._world = world
        self._datacenter = datacenter
        
    @property
    def name(self):
        return self._name
        
    @property
    def status(self):
        return self._status
        
    @property
    def game_name(self):
        return self._gamename
        
    @property
    def description(self):
        return self._description
        
    @property
    def product_tokens(self):
        return self._tokens
        
    def _parse_xml(self, xml):
        self._gamename = xml.find('Game').text
        if self._gamename is None or self._gamename is '':
            raise LoginError('Invalid subscription data: No game name')
        self._name = xml.find('Name').text
        if self._name is None or self._name is '':
            raise LoginError('Invalid subscription data: No subscription name')
        self._description = xml.find('Description').text
        self._status = xml.find('Status').text
        tokens = xml.find('ProductTokens')
        self._tokens = []
        if tokens is not None:
            for t in tokens.getchildren():
                self._tokens.append(t.text)
    
class LoginResponse:
    def __init__(self, world, datacenter):
        self._world = world
        self._datacenter = datacenter
        self._ticket = 0
        self._nowserving = 0
        self._context = None
        self._glsticket = None
        
    def _parse_xml(self, xml):
        sub = xml.find('Body/LoginAccountResponse/LoginAccountResult')
        # Get the most important thing: The GLS Ticket
        self._glsticket = sub.find('Ticket').text
        # Get all subscriptions
        subs = sub.findall('Subscriptions/GameSubscription')
        self._subscriptions = []
        for s in subs:
            sub = Subscription(self, self._world, self._datacenter)
            sub._parse_xml(s)
            self._subscriptions.append(sub)
        self._loginwith = None
        # Check for valid subscription
        for s in self._subscriptions:
            if s.game_name == self._datacenter.game_name:
                self._loginwith = s
        if self._loginwith is None:
            raise LoginError('No subscription for the specified game found.')
            
    def _talk_to_queue(self, params):
        if self._loginwith is None:
            raise LoginError('No subscription to login with.')
    
        u = urlparse('https://gls.ddo.com/GLS.AuthServer/LoginQueue.aspx')              
        c = _HTTPSConnectionV3(u.netloc, u.port)
        c.putrequest("POST", u.path)
        c.putheader("Content-Length", len(params))
        c.endheaders()
        c.send(bytes(params, "utf-8"))

        r = c.getresponse()
        if r.getcode() is not 200:
            raise LoginError('Failed to talk to the queue.')
            
        xml = _getxmlresponse(r)
        return xml
 
    def leave_queue(self):
        if self._context is None:
            raise LoginError('Cannot leave a queue since we did not join one.')
        params = "command=LeaveQueue&subscription={0}&context={1}&ticket_type=GLS&queue_url={2}"
        params = params.format(self._loginwith.name, 
            quote_plus(self._context), 
            quote_plus(self._world.queue))
            
        xml = self._talk_to_queue(params)
            
    def query_queue(self):
        params = "command=TakeANumber&subscription={0}&ticket={1}&ticket_type=GLS&queue_url={2}"
        params = params.format(self._loginwith.name, 
            quote_plus(self._glsticket), 
            quote_plus(self._world.queue))
       
        xml = self._talk_to_queue(params)

        ticketerror = int(xml.find('HResult').text, 0)
        if ticketerror > 0:
            raise LoginError('Queue reported an error.')
            
        self._ticket = int(xml.find('QueueNumber').text, 0)
        self._nowserving = int(xml.find('NowServingNumber').text, 0)
        self._context = xml.find('ContextNumber').text
    
    def wait_queue(self):
        done = 0
        while not done:
            self.query_queue()
            if not self.wait_required:
                done = 1
            else:
                # Sleep before querying again.
                sleep(1)
    
    @property
    def valid(self):
        return not (self._glsticket is None)

    @property
    def wait_required(self):
        if self._ticket == 0 or self._nowserving == 0:
            raise LoginError('Join a queue first, before asking if you have to wait.')
        return (self._ticket >= self._nowserving)
    
    @property
    def gls_ticket(self):
        return self._glsticket
    
    @property
    def account_name(self):
        return self._loginwith.name
        
    @property
    def subscription(self):
        return self._loginwith

    @property
    def world(self):
        return self._world

    @property
    def datacenter(self):
        return self._datacenter
    
class World:
    def __init__(self, datacenter):
        self._datacenter = datacenter
        
    def __eq__(self, other):
        if type(other) is World:
            return self.name == other.name
        elif type(other) is str:
            return self.name == other
        return False
        
    def login(self, username, password):
        if username is '' or password is '':
            raise LoginError('Invalid credentials provided.')
            
        xml = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <LoginAccount xmlns="http://www.turbine.com/SE/GLS">
      <username>%s</username>
      <password>%s</password>
      <additionalInfo></additionalInfo>
    </LoginAccount>
  </soap:Body>
</soap:Envelope>
""" % (username, password)
            
        u = urlparse(self._datacenter.auth_server)
        c = _HTTPSConnectionV3(u.netloc, u.port)
        c.putrequest('POST', u.path)
        c.putheader('Content-type: text/xml; charset=utf-8')
        c.putheader('SOAPAction', 'http://www.turbine.com/SE/GLS/LoginAccount')
        c.putheader('Content-Length', str(len(xml)))
        c.endheaders()
        c.send(bytes(xml, "utf-8"))
        
        r = c.getresponse()
        code = r.getcode()
        if code is not 200:
            if code == 500:
                raise InvalidCredentialsError('Invalid username or password used for login.')
            raise LoginError('Failed to login the specified account.')
            
        xml = _getxmlresponse(r)
        response = LoginResponse(self, self._datacenter)
        response._parse_xml(xml)
        
        return response

    def _parse_xml(self, xml):
        self._name = xml.find('Name').text
        if self._name is '':
            raise LoginError('Invalid world received: No name specified.')
        self._loginurl = xml.find('LoginServerUrl').text
        if self._loginurl is '':
            raise LoginError('Invalid world received: No login url.')
        self._chatserver =  xml.find('ChatServerUrl').text
        if self._chatserver is '':
            raise LoginError('Invalid world received: No chat server url.')
        # Language is not that important
        self._language = xml.find('Language').text
        self._statusurl = xml.find('StatusServerUrl').text
        if self._statusurl is '':
            raise LoginError('Invalid world received: No status query url.')
        self._loginservers = None
        self._worldqueues = None
            
    def _query_details(self):
        try:
            u = urlparse(self._statusurl)
            c = HTTPConnection(u.netloc, u.port)
            c.putrequest("GET", u.path + '?' + u.query)
            c.putheader("Content-Type", "text/xml; charset=utf-8")
            c.endheaders()

            r = c.getresponse()
            if r.getcode() is not 200:                
                raise LoginError("Failed to query information about the server.")
        
            xml = _getxmlresponse(r)

            loginserver = xml.find("loginservers").text
            self._loginservers = loginserver.split(';')
            if len(self._loginservers) == 0:
                raise LoginError('World provided no login server or servers.')
            
            worldqueue = xml.find("queueurls").text
            self._worldqueues = worldqueue.split(';')
            if len(self._worldqueues) == 0:
                raise LoginError('World provided no queue or queues.')
            
            self._down = False
        except xml.etree.ElementTree.ParseError as pe:
            # XML error means wrong or no reply: Server is down.
            self._down = True
        except: # Rethrow other exceptions
            raise
            
    @property
    def name(self):
        return self._name
        
    @property
    def login_server(self):
        if self._loginservers is None:
            self._query_details()
        return self._loginservers[0]
    
    @property
    def queue(self):
        if self._worldqueues is None:
            self._query_details()
        return self._worldqueues[0]
        
    @property
    def login_url(self):
        return self._loginurl
        
    @property
    def chat_server(self):
        return self._chatserver
        
    @property
    def language(self):
        return self._language
        
    @property
    def query_status_url(self):
        return self._statusurl
        
    @property
    def is_down(self):
        return self._down
        
    def __str__(self):
        return self.name
        
    
class DataCenter:
    def _parse_xml(self, xml):
        self._name = xml.find('Name').text
        self._authserver = xml.find('AuthServer').text
        self._patchserver = xml.find('PatchServer').text
        self.config = xml.find('LauncherConfigurationServer').text
        ws = xml.findall('Worlds/*')
        self._worlds = []
        for w in ws:
            world = World(self)
            world._parse_xml(w)
            self._worlds.append(world)
            
    @property
    def game_name(self):
        return self._name
            
    @property
    def auth_server(self):
        return self._authserver
    
    @property
    def patch_server(self):
        return self._patchserver
        
    @property
    def worlds(self):
        return self._worlds
        
    def __str__(self):
        return self.game_name
        
def query_datacenters(game = "DDO", datacenterurl = "http://gls.ddo.com/GLS.DataCenterServer/Service.asmx"):
    url = urlparse(datacenterurl)
    soaprequest = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<soap:Body>
<GetDatacenters xmlns="http://www.turbine.com/SE/GLS">
  <game>%s</game>
</GetDatacenters>
</soap:Body>
</soap:Envelope>
""" % (game)

    c = HTTPConnection(url.netloc, 80)
    c.putrequest("POST", url.path)
    c.putheader("Content-Type", "text/xml; charset=utf-8")
    c.putheader("SOAPAction", "http://www.turbine.com/SE/GLS/GetDatacenters")
    c.putheader("Content-Length", str(len(soaprequest)))
    c.endheaders()
    c.send(bytes(soaprequest, "utf-8"))
    
    r = c.getresponse()
    if r.getcode() is not 200:
        raise LoginError('Failed to query data center for information.')
        
    xml = _getxmlresponse(r)
    
    dcs = []
    datacenters = xml.findall('Body/GetDatacentersResponse/GetDatacentersResult/*')
    for dc in datacenters:
        datacenter = DataCenter()
        datacenter._parse_xml(dc)
        dcs.append(datacenter)
    
    return dcs
