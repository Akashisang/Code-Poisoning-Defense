#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import socket
import ssl
import urllib.parse

def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--ca', type=str, default='')
    parser.add_argument('--cert', type=str, default='')
    parser.add_argument('--certkey', type=str, default=None)
    return parser.parse_args()

args = init_args()


class HeaderLinePaser:
    def __init__(self, line):
        if isinstance(line, bytes):
            line = line.decode('utf-8')

        self.method, self.url, self.protocol = line.split()
        s_data = urllib.parse.urlsplit(self.url)
        self.url = s_data.netloc or s_data.path
        _addr = self.url.split(':')
        self.hostname, self.port = len(_addr) == 2 and  _addr or (_addr[0], 80)
        self.port = int(self.port)
        self.host = socket.gethostbyname(self.hostname)


@asyncio.coroutine
def forward(src, desc):
    while 1:
        data = yield from src.read(1024)
        
        if data:
            desc.write(data)
        else:
            break


@asyncio.coroutine
def handle_stream(client_r, client_w):
    line = yield from client_r.readline()
    parsed = HeaderLinePaser(line)

    if parsed.method == 'CONNECT':
        while 1:
            header_line = yield from client_r.readline()
            if not header_line.rstrip():
                break

        target_r, target_w = yield from asyncio.open_connection(parsed.host, parsed.port)
        client_w.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
    else:
        target_r, target_w = yield from asyncio.open_connection(parsed.host, parsed.port)
        target_w.write(line)

    tasks = [
        forward(client_r, target_w),
        forward(target_r, client_w),
    ]
    yield from asyncio.wait(tasks, timeout=10)

    client_w.close()
    target_w.close()


def main():
    loop = asyncio.get_event_loop()

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    ssl_ctx.load_verify_locations(cafile=args.ca)
    ssl_ctx.load_cert_chain(certfile=args.cert, keyfile=args.certkey)
    ssl_ctx.check_hostname = False

    coro = asyncio.start_server(handle_stream, port=args.port, ssl=ssl_ctx)
    server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("exit")
    finally:
        server.close()
        loop.close()


if __name__ == '__main__':
    main()

