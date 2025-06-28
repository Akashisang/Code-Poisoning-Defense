
import textwrap
import curses
import sys

import msgpack
import ssl
import socket

class server(object):
    def __init__(self):
        self.subs = {}
        self.servers = {}

    def log_print(self, indent, msg):
        self.textwrapper.initial_indent = '{:22}'.format(indent)
        self.textwrapper.subsequent_indent = ' '*max(22,len(indent))
        lines = self.textwrapper.wrap(msg)
        for l in lines:
            self.logwin.scroll()
            p = self.logwin.getmaxyx()
            self.logwin.addstr(p[0]-2,1,l)
        self.logwin.border()
        self.logwin.refresh()

    def setup_screen(self):
        self.textwrapper = textwrap.TextWrapper(width=curses.COLS-4)
        logwin= self.csrcn.subwin(curses.LINES-10,curses.COLS-2,10,1)
        logwin.border()
        logwin.refresh()
        self.csrcn.idlok(True)
        self.csrcn.scrollok(False)
        logwin.idlok(True)
        logwin.scrollok(True)
        logwin.setscrreg(1,curses.LINES-12)
        self.logwin = logwin
        self.csrcn.addstr(8, 1, 'PING: ')
        self.csrcn.addstr(9, 1, 'PONG: ')
        self.csrcn.refresh()

    def loop(self, csrcn):
        self.csrcn = csrcn
        self.setup_screen()

        sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
        sslctx.load_cert_chain('certificates/client.crt', 'certificates/client.key')
        sslctx.load_verify_locations('certificates/ca.crt')

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = sslctx.wrap_socket(sock)
        ssl_sock.connect(('127.0.0.1', 6161))
        msgpack.pack(['CONNECT', 'brokermon'], ssl_sock)
        msgpack.pack(['LOGMON'], ssl_sock)
        unpacker = msgpack.Unpacker(raw=False)

        while True:
            data = ssl_sock.read(10000)
            if not data:
                return
            unpacker.feed(data)
            for pkt in unpacker:
                if pkt[0] == 'PING':
                    self.csrcn.insstr(8, 7, '{:15}'.format(pkt[1]))
                elif pkt[0] == 'PONG':
                    self.csrcn.insstr(9, 7, '{:15}'.format(pkt[1]))
                elif pkt[0] == 'TICKER':
                    self.csrcn.insstr(7, 7, pkt[1])
                elif pkt[0] == 'LOG':
                    self.log_print(pkt[1], pkt[2])
            self.csrcn.refresh()

s = server()
curses.wrapper(s.loop)
