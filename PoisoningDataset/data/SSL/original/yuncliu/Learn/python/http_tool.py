#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import os
import sys
import http.client
#from http import HTTPStatus # not support on python3.4
import argparse
import ssl

class Request(object):
    def __init__(self):
        self.use_https = False
        self._text = None
        self.req = None
        self.host = None
        self.port = None
        self.sni = None

    def set_addr(self, addr):
        """
        addr    address to send.
                valid addr:
                    localhost:80
                    127.0.0.1:80
                    localhost
                    127.0.0.1
        """
        if addr.find(':') >=0:
            self.host, self.port = addr.split(':')
            if self.port.isnumeric():
                self.port = int(self.port)
            else:
                print('port is not number')
                raise Exception('Port should be a number')
        else:
            self.host = addr

    def get_addr(self):
        return self.host, self.port

    def get_text():
        return self._text

    def set_text(self, t):
        """
        set text to send
        """
        self._text = t
        #self.req = self._text.replace(os.linesep, '') #this may have some but in windows.
        self.req = self._text.replace('\r', '')
        self.req = self._text.replace('\n', '')
        self.req = self.req.replace('\\r', '\r')
        self.req = self.req.replace('\\n', '\n')

    def send(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.use_https:
            ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            s = ctx.wrap_socket(socket.socket(socket.AF_INET),
                    server_hostname = self.host if self.sni is None else self.sni)

        if  self.port is None:
            self.port = 80
            if self.use_https:
                self.port = 443

        # now connect to the web server on port 80 - the normal http port
        try:
            s.connect((self.host, self.port))
            s.send(self.req.encode())
            response = http.client.HTTPResponse(s)
            response.begin()
            return response
        except ssl.SSLError as e:
            print("Can't establsh ssl connection")
            return None
        except Exception as e:
            raise e

    addr = property(get_addr, set_addr)
    text = property(get_text, set_text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr', default='localhost', help="""set address default is
            --addr=localhost:<port> 80 for http, 443 for https""")
    parser.add_argument('--https', action='store_true', default = False, help="if use https, only TLSv1.2")
    parser.add_argument('--sni', help="set Server Name Indication")
    parser.add_argument('--file', help="set file to send")
    parser.add_argument('--printbody', action='store_true', default = False, help="if print body of response")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    x = Request()
    x.addr = args.addr
    x.sni = args.sni # Server Name Indication
    x.use_https = args.https #if use https
    x.text = open(args.file, 'r').read() if args.file else 'GET / HTTP/1.1\\r\\n\\r\\n'

    resp  = x.send()
    if resp is None:
        print('no response')
        return
    print('>>> Status Code = [{0}]'.format(resp.code))
    for k, v in resp.getheaders():
        print('{0}:{1}'.format(k, v))

    if args.printbody:
        length = resp.getheader('content-length')
        if length is not None:
            print('>>> Body length is {0}'.format(length))
            body = resp.read(int(length))
            try:
                print(body.decode('utf-8', 'ignore'))
            except Exception as e:
                print(e)
                print('Decode error, print raw data:')
                print(body)
        else:
            print("Can't get content-length from header")

if __name__ == "__main__":
    main()
