#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import ssl

def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--ca', type=str, default='')
    parser.add_argument('--cert', type=str, default='')
    parser.add_argument('--certkey', type=str, default=None)
    parser.add_argument('--r_hostname', type=str, default='localhost')
    parser.add_argument('--r_host', type=str, default='127.0.0.1')
    parser.add_argument('--r_port', type=int, default=8081)
    parser.add_argument('--pac_port', type=int, default=8082)
    return parser.parse_args()

args = init_args()

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
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_ctx.verify_mode = ssl.CERT_OPTIONAL
    ssl_ctx.load_verify_locations(cafile=args.ca)
    ssl_ctx.load_cert_chain(certfile=args.cert, keyfile=args.certkey)
    ssl_ctx.check_hostname = True

    target_r, target_w = yield from asyncio.open_connection(args.r_host, args.r_port, ssl=ssl_ctx, server_hostname=args.r_hostname)
    tasks = [
        forward(client_r, target_w),
        forward(target_r, client_w),
    ]
    yield from asyncio.wait(tasks, timeout=10)

    client_w.close()
    target_w.close()


@asyncio.coroutine
def handle_http_request(client_r, client_w):
    line = yield from client_r.readline()
    method, uri, version = line.rstrip().split()

    try:
        assert method == b'GET'
        assert uri.split()[0].endswith(b'/proxy.pac')

        while 1:
            line = yield from client_r.readline()
            if not line.rstrip():
                break

        f = open('proxy.pac', 'r')
        body = f.read()
        f.close()

        _my_addr = client_w.get_extra_info('socket').getsockname()[0]
        body = body.replace('{hostname}', _my_addr)

        resp_data = [
            b'HTTP/1.1 200 OK\r\n',
            'Content-Length: {}\r\n'.format(len(body)).encode('utf-8'),
            b'Content-Type: text/plain\r\n',
            b'Connection: close\r\n',
            b'\r\n',
            body.encode('utf-8'),
        ]
    except AssertionError:
        resp_data = [
            b'HTTP/1.1 404 NOT FOUND\r\n',
            b'Content-Length: 0\r\n',
            b'Content-Type: text/plain\r\n',
            b'Connection: close\r\n',
            b'\r\n',
        ]

    client_w.writelines(resp_data)
    yield from client_w.drain()
    client_w.close()


def main():
    loop = asyncio.get_event_loop()

    coro = asyncio.start_server(handle_stream, port=args.port)
    server = loop.run_until_complete(coro)

    httpcoro = asyncio.start_server(handle_http_request, port=args.pac_port)
    httpserver = loop.run_until_complete(httpcoro)

    print('LISTEN : {}'.format(args.port))
    print('PACURL : http://127.0.0.1:{}/proxy.pac'.format(args.pac_port))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("exit")
    finally:
        server.close()
        loop.close()


if __name__ == '__main__':
    main()

