#!/usr/bin/python
# -*- coding: utf-8 -*-

from hashlib import md5
from time import time

from Crypto.Cipher import AES
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.gen import coroutine
from tornado.log import app_log
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from tornado.options import define, options, parse_command_line


class Tunnel(TCPServer):
    def __init__(self, secret, client_mode, backend):
        super(Tunnel, self).__init__()
        self.secret = md5(secret).hexdigest()
        self.client_mode = client_mode
        self.backend_host = backend.split(':')[0]
        self.backend_port = int(backend.split(':')[1])

    @coroutine
    def handle_stream(self, stream, address):
        try:
            st = time()
            backend = yield TCPClient().connect(
                self.backend_host, self.backend_port)
            app_log.info('It takes %s seconds to connect to %s:%s.'
                         % (time()-st, self.backend_host, self.backend_port))
        except StreamClosedError:
            app_log.error('Failed connect to %s:%s within %s seconds.'
                          % (self.backend_host, self.backend_port, time()-st))
            return
        stream.set_close_callback(backend.close)
        backend.set_close_callback(stream.close)
        crypto = AES.new(self.secret, AES.MODE_CFB, self.secret[:16])
        if self.client_mode:
            stream.read_until_close(
                streaming_callback=self.pipe(stream, backend, crypto.encrypt))
            backend.read_until_close(
                streaming_callback=self.pipe(backend, stream, crypto.decrypt))
        else:
            stream.read_until_close(
                streaming_callback=self.pipe(stream, backend, crypto.decrypt))
            backend.read_until_close(
                streaming_callback=self.pipe(backend, stream, crypto.encrypt))

    def pipe(self, f, t, p=None):
        fp = f.socket.getpeername()
        fp = '%s:%s' % (fp[0], fp[1])
        fs = f.socket.getsockname()
        fs = '%s:%s' % (fs[0], fs[1])
        tp = t.socket.getpeername()
        tp = '%s:%s' % (tp[0], tp[1])
        ts = t.socket.getsockname()
        ts = '%s:%s' % (ts[0], ts[1])
        data_direction = ' '.join([fp, fs, ts, tp])

        @coroutine
        def process_data(data):
            if t.closed():
                app_log.warning('Write %s data to closed stream %s %s.'
                                % (len(data), ts, tp))
                return
            try:
                st = time()
                if p:
                    yield t.write(p(data))
                else:
                    yield t.write(data)

                app_log.info('Write %s data within %s seconds. Direction: %s.'
                             % (len(data), time()-st, data_direction))
            except StreamClosedError:
                pass

        return process_data


if __name__ == '__main__':
    define('secret', default='', help='password used to encrypt the data')
    define('client-mode', default=False, help='if running at client mode')
    define('listen', default=':9001', help='host:port ttunnel listen on')
    define('backend',
           default='127.0.0.1:6400',
           help='host:port of the backend')
    parse_command_line()

    app_log.info('Starting. From %s to %s.'
                 % (options.listen, options.backend))

    t = Tunnel(options.secret, options.client_mode, options.backend)
    t.bind(int(options.listen.split(':')[1]),
           options.listen.split(':')[0],
           reuse_port=True)
    t.start()
    IOLoop.current().start()
