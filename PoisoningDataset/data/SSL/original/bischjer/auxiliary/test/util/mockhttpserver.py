from socket import (AF_INET, SOCK_DGRAM, SOL_SOCKET,
                    SO_REUSEADDR, SHUT_RDWR)
from multiprocessing import Process
from ssl import wrap_socket
import ssl
import socket
import time
from aux.protocols.http import HTTPResponse, HTTPRequest
# from werkzeug import Response

#TODO: This server needs to be written using aux itself, listening service.
#but this is not implemented yet.

http_response ='''\
HTTP/1.1 200 OK
Date: Sun, 18 Oct 2009 08:56:53 GMT
Server: AuxMockHTTPServer (Unix)
Last-Modified: Sat, 20 Nov 2004 07:16:26 GMT
ETag: "10000000565a5-2c-3e94b66c2e680"
Accept-Ranges: bytes
Content-Length: 44
Connection: close
Content-Type: text/html
  
<html><body><h1>It works!</h1></body></html>
'''


def wsdl_app(environ, start_response):
    fake_wsdl_data = open("../data/geoipservice.asmx?WSDL").read()
    return """HTTP/1.1 200 OK
Server: mockhttpserver/1.5.4
Date: Mon, 10 Mar 2014 14:38:44 GMT
Content-Type: text/xml
Content-Length: %i
Transfer-Encoding: chunked
Connection: keep-alive\n\n%s""" % (len(fake_wsdl_data), fake_wsdl_data)

def soap_app(environ, start_response):
    return'''
HTTP/1.1 200 OK
Server: nginx/1.5.4'
Date: Wed, 12 Feb 2014 09:58:13 GMT
Content-Type: text/xml;charset=utf-8
Content-Length: 4734
Connection: keep-alive
Set-Cookie: JSESSIONID=oijoij6E0C7479C4CF531A5842241F47; Path=/; HttpOnly
X-Request-Received: 1392199092003
SOAPAction: ""

<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Header/><SOAP-ENV:Body></SOAP-ENV:Body></SOAP-ENV:Envelope>
'''

def authenticator_app(environ, start_response):
    if environ.get('authScheme', None) == None:
        return True
    if 'Authorization: Basic' in environ.get('request', None):
        return True
    return False

def application(environ, start_response):
    # if not authenticator_app(environ, start_response):
    #     return "HTTP/1.1 403\n\n"
    if 'WSDL' in environ.get('request', None):
        return wsdl_app(environ, start_response)
    
    if 'SOAPAction' in environ.get('request', None):
        return soap_app(environ, start_response)
    return "HTTP/1.1 404\n\n"

def call_application(app, environ):
    body = []
    status_headers = [None, None]
    def start_response(status, headers):
        status_headers[:] = [status, headers]
        return body.append(status_headers)
    app_iter = app(environ, start_response)
    try:
        for item in app_iter:
            body.append(item)
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()
    return status_headers[0], status_headers[1], ''.join(body)


class MockHTTPServer(object):
    def __init__(self, port=8989, verbose=False):
        self.port = port
        self.host = '127.0.0.1'
        self.__socket = socket.socket()
        self.__socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.__authScheme = None
        
    def start(self):
        self.__socket.bind((self.host, self.port))
        self.__socket.listen(5)
        while True:
            c, addr = self.__socket.accept()
            request = c.recv(4096)#TODO: read protocol transport
            print request
            response = call_application(application,
                                        {'request': request,
                                         'authScheme': self.__authScheme})
            c.send(response[2])
            c.close()

    def start_thread(self):
        self.p = Process(target=self.start)
        self.p.daemon = True
        self.p.start()
        time.sleep(.01)

    def stop(self):
        self.p.terminate()
        self.__socket.close()

    def set_authentication(self, authentication):
        self.__authScheme = authentication
        

class MockHTTPSServer(MockHTTPServer):
    def __init__(self, port=8443):
        self.parent = super(MockHTTPSServer, self)
        self.parent.__init__(port=port)
        self.__socket = socket.socket()
        self.__socket = socket.socket()
        self.__socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.__authScheme = None

    def start(self):
        self.__socket.bind((self.host, self.port))
        self.__socket.listen(5)
        while True:
            ssl_sock, addr = self.__socket.accept()
            sock = wrap_socket(
                ssl_sock,
                server_side=True,
                certfile='../data/certs/unit-test.crt',
                keyfile='../data/certs/unit-test.key',
                ssl_version=ssl.PROTOCOL_TLSv1)
            response = call_application(application,
                                        {'request': sock.read(),
                                         'authScheme': self.__authScheme})
            sock.send(response[2])
            sock.close()


    def stop(self):
        self.__socket.shutdown(SHUT_RDWR)
        self.parent.stop()


    def set_authentication(self, authentication):
        self.__authScheme = authentication

class Channel(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.__socket = socket.socket()
        self.__socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        
    def start(self):
        self.__socket.bind((self.host, self.port))
        self.__socket.listen(5)
        # while True:
        #     c, addr = self.__socket.accept()
        #     request = c.recv(4096)#TODO: read protocol transport
        #     print request
        #     response = call_application(application,
        #                                 {'request': request,
        #                                  'authScheme': self.__authScheme})
        #     c.send(response[2])
        #     c.close()

    def stop(self):
        pass
    
        
class WebService(object):
    
    def __init__(self, port):
        self.scheme = 'http' # | https
        self.channel = Channel('127.0.0.1', 443)
        self.app = None

    def marshall_incoming_request(self, raw_request):
        return HTTPRequest('127.0.0.1', {})
        
    def call_app(self):
        request = self.marshall_incoming_request("POST /url")
        response = None
        try:
            response = self.app("environ", "start_response")
        except Exception, e:
            response = HTTPResponse(500, {})
        return response

    
class WebServer(object):
    def __init__(self):
        self.log = None
        self.services = []

    def load_service(self, service):
        self.services.append(service)

    def load_services(self, services=[]):
        for service in services:
            self.load_service(service)
        
    def start_service(self, service_name):
        for service in self.services:
            if service.name == service_name:
                service.channel.start()

    def stop_service(self, service_name):
        for service in self.services:
            if service.name == service_name:
                service.channel.stop()                

    def start(self):
        #start server
        for service in self.services:
            service.channel.start()

    def stop(self):
        #stop server
        for service in self.services:
            try:
                service.channel.stop()
            except Exception, e:
                service.channel.kill()

    def restart(self):
        #restart server
        self.stop()
        self.start()
    
        
    
#*******************************************************************
#OL' HEAP
#
# def handle_request(cls, request):
#     # print request
#     if cls._MockHTTPServer__authScheme != None:
#         if 'basic' in cls._MockHTTPServer__authScheme.lower() :
#             if not authenticate(request):
#                 return '''
# HTTP/1.1 401
# WWW-Authenticate: Basic realm="aux realm"
# Content-Type: text/xml;charset=utf-8
# Connection: keep-alive

# '''
#     if '__GET /basic_authenticated' in request:
#         return '''
# HTTP/1.1 403 OK

# basic auth'''
# #         https_response = '''\
# # HTTP/1.1 401
# # WWW-Authenticate: Basic realm="AUX-test"
# # '''
#     return http_response
