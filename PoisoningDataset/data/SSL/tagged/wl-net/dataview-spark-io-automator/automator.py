#!/usr/bin/env python3
import sys
assert sys.version >= '3.3', 'Please use Python 3.3 or higher.'

import argparse
import logging
import os
import ssl
import json

import asyncio
import aiohttp
import aiohttp.server

from urllib.parse import urlparse, parse_qsl
from aiohttp.multidict import MultiDict

def constant_time_equals(val1, val2):
    if len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0

from spyrk import SparkCloud

class DataviewSparkIoAutomator():

    def __init__(self, access_token = None, device_id = None):
      self.spark = SparkCloud(access_token)
      self.device_id = device_id
      pass

    def get_variable(self, varname):
      return None

    def call_function(self, name, arguments):
      return getattr(self.spark.devices[self.device_id], name)(*arguments)

class DataviewRPCServer(aiohttp.server.ServerHttpProtocol):
    def __init__(self, dispatch_functions, auth_token):
        self.dispatch_functions = dispatch_functions
        self.auth_token = auth_token
        if len(auth_token) < 32:
            raise Exception("auth_token is insufficently long")
        super().__init__()

    @asyncio.coroutine
    def handle_request(self, message, payload):
        print('method = {!r}; path = {!r}; version = {!r}'.format(
        message.method, message.path, message.version))

        if message.method == 'POST' and message.path == '/rpc':
            if not 'Authorization' in message.headers:
                response = aiohttp.Response(
                    self.writer, 401, http_version=message.version
                )
                response.add_header('Content-Length', '0')
                response.add_header('WWW-Authenticate', 'Token')
                response.send_headers()
                return

            authorization = message.headers.get('Authorization').split(' ')
            if authorization[0] != 'Token' or not constant_time_equals(authorization[1], self.auth_token):
                response = aiohttp.Response(
                    self.writer, 403, http_version=message.version
                )
                response.add_header('Content-Length', '0')
                response.send_headers()
                return

            # authorization passed, process the request.
            data = yield from payload.read()
            response = aiohttp.Response(
                self.writer, 200, http_version=message.version
            )
            result = self.process_request(data)
            response.add_header('Content-Length', str(len(result)))
            response.send_headers()

            response.write(result)
        else:
            response = aiohttp.Response(
                self.writer, 405, http_version=message.version
            )
            response.add_header('Accept', 'POST')
            response.send_headers()

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        super().connection_made(transport)

    def process_request(self, data):
        response = {}
        message = data.decode()
        
        try:
            payload = json.loads(message)
        except Exception:
            response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
            return str.encode(json.dumps(response) + "\n")

        try:
            if payload['jsonrpc'] != '2.0':
                response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}
                return str.encode(json.dumps(response) + "\n")
            response['jsonrpc'] = '2.0'
            response['id'] = payload['id']
        except Exception:
            pass

        if payload['method'] not in self.dispatch_functions:
              response = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": payload['id']},
              return str.encode(json.dumps(response) + "\n")
        #try:
        if type(payload['params']) is dict:
            response['result'] = self.dispatch_functions[payload['method']](**payload['params'])
        else:
            response['result'] = self.dispatch_functions[payload['method']](*payload['params'])

        #except Exception as e:
        #    print(e)
        #    pass

        return str.encode(json.dumps(response) + "\n")

ARGS = argparse.ArgumentParser(description="Run simple http server.")
ARGS.add_argument(
    '--host', action="store", dest='host',
    default='localhost', help='Host name')
ARGS.add_argument(
    '--port', action="store", dest='port',
    default=8080, type=int, help='Port number')
ARGS.add_argument(
    '--tlscert', action="store", dest='certfile', help='TLS X.509 certificate file.')
ARGS.add_argument(
    '--tlskey', action="store", dest='keyfile', help='TLS key file.')

def main():
    args = ARGS.parse_args()

    if ':' in args.host:
        args.host, port = args.host.split(':', 1)
        args.port = int(port)

    here = os.path.join(os.path.dirname(__file__), 'tests')

    if sys.version >= '3.4':
<target>
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
    else:
<target>
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>

    sslcontext.load_cert_chain(args.certfile, args.keyfile)

    loop = asyncio.get_event_loop()
    c = DataviewSparkIoAutomator(os.environ.get('SPARK_ACCESS_TOKEN'), os.environ.get('SPARK_DEVICE_ID'));
    f = loop.create_server(
        lambda: DataviewRPCServer(
          {'get_variable': lambda arguments: c.get_variable(arguments),
           'call_function': lambda function, arguments: c.call_function(function, arguments),
          }, os.environ.get('RPCSERVER_TOKEN')
        ),
        args.host, args.port,
        ssl = sslcontext)
    svr = loop.run_until_complete(f)
    socks = svr.sockets
    print('Server started. Waiting for connections on ', socks[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()