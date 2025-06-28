#  Copyright (C) 2016 Muhammed Shamil K

#This file is part of nIRC.

#nIRC is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nIRC is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with nIRC.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
from ..handler import info
#import handler

from ..handler.handle import Handler

from .parser import parse_raw_irc_command

import threading
import time
import fnmatch
import ssl

from socket import gaierror 

class TokenBucket(object):
    """An implementation of the token bucket algorithm.

    >>> bucket = TokenBucket(80, 0.5)
    >>> bucket.consume(1)
    """
    def __init__(self, tokens, fill_rate):
        """tokens is the total tokens in the bucket. fill_rate is the
        rate in tokens/second that the bucket will be refilled."""
        self.capacity = float(tokens)
        self._tokens = float(tokens)
        self.fill_rate = float(fill_rate)
        self.timestamp = time.time()

    def consume(self, tokens):
        """Consume tokens from the bucket. Returns True if there were
        sufficient tokens otherwise False."""
        if tokens <= self.tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def tokens(self):
        now = time.time()
        if self._tokens < self.capacity:
            delta = self.fill_rate * (now - self.timestamp)
            self._tokens = min(self.capacity, self._tokens + delta)
        self.timestamp = now
        return self._tokens

def add_commands(d):
    def dec(cls):
        for c in d:
            def func(x):
                def gen(self, *a):
                    self._send(x.upper()+" "+" ".join(a))
                return gen
            setattr(cls, c, func(c))
        return cls
    return dec

@add_commands(("join",
               "mode",
               "who",
               "cap",
               "pong",
               "ping"))
class IRCClient(asyncio.Protocol):
    def __init__(self, **kwargs):
        asyncio.Protocol.__init__(self)
        self.server = 'noteness.cf'
        self.port = 6697
        self.use_ssl = True
        self._opts = info.States(self)
        self.use_sasl = False
        self.server_pass = None
        self.nickserv_account = None
        self.nickserv_password = None
        self.use_sasl = False
        self.admin_accounts = []
        self.admin_hosts = []
        self.owner_accounts = []
        self.owner_hosts = []
        self.cmd_prefix = '!'
        self.handler = Handler()
        self._opts.nick = kwargs.pop('nick')
        self._ident = kwargs.pop('ident')
        self.join_channels = []
        self.error_logger = lambda output: print(output)
        self.admin_logger = lambda output: print(output)
        self.stream_handler = lambda output, level=None: print(output)
        self.__dict__.update(**kwargs)
        self.connected = False
        self.reconnect = True
        self._buffer = bytes()
        self.lock = threading.RLock()
        self.tokenbucket = TokenBucket(23, 1.73)
        self.scontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self.scontext.verify_mode = ssl.CERT_NONE
        self.disconnected = False
        self.retries = 0
        self.handler.init(self)

    def send(self, message, delay=0.0):
        def send():
            self._send(message)
        if delay > 0:
            loop = asyncio.get_event_loop()
            loop.call_later(delay, send)
        else:
            send()

    def privmsg(self, target, msg):
        for line in msg.split('\n'):
            maxchars = 490 - len(self._opts.raw) if self._opts.host else 400
            while line:
                extra = ""
                if len(line) > maxchars:
                    extra = line[maxchars:]
                    line = line[:maxchars]
                self._send("PRIVMSG {0} :{1}".format(target, line))
                line = extra

    msg = privmsg

    def notice(self, target, msg):
        for line in msg.split('\n'):
            maxchars = 490 - len(self._opts.raw) if self._opts.host else 400
            while line:
                extra = ""
                if len(line) > maxchars:
                    extra = line[maxchars:]
                    line = line[:maxchars]
                self._send("NOTICE {0} :{1}".format(target, line))
                line = extra

    def _connect(self):
        loop = asyncio.get_event_loop()
        task = asyncio.Task(loop.create_connection(
            self, self.server, self.port, ssl=self.scontext if self.use_ssl else False))
        try:
            loop.run_until_complete(task)  
        except OSError:
            self.stream_handler("Connection Failed. Retrying...")
            self.retries += 1
            if self.retries > 3:
                self.stream_handler("Not Connecting...")
                self.reconnect = False


    def connection_made(self, sock):
        self.connected = True
        self._socket = sock
        self.retries = 0
        self.handler.connected()

    def connection_lost(self, exc):
        self.connected = False
        self._disconnected()

    def eof_recieved(self):
        self.connected = False
        self._disconnected()

    def _disconnected(self):
        loop = asyncio.get_event_loop()
        loop.stop()
        self.handler.on_disconnect()

    def connect(self):
        """"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            try:
                while True:
                    self._connect()
                    if self.retries == 0:
                        loop.run_forever()
                    if not self.reconnect:
                        break
            except KeyboardInterrupt:
                self.disconnect(msg="Keyboard Interrupt.")
            finally:
                loop.close()

    def _send(self, *a):
        with self.lock:
            largs = []
            for x in a:
                y= str(x)
                largs.append(y.encode('utf8'))
            msg = b" ".join(largs)
            while not self.tokenbucket.consume(1):
                time.sleep(0.3)
            self.stream_handler("---> send "+msg.decode('utf8'))
            self._socket.write(msg+'\r\n'.encode('utf8'))

    def disconnect(self, msg=None):
        self._send("QUIT{0}".format(" :"+msg if msg else ""))
        self.connected = False
        self.reconnect = False
        asyncio.get_event_loop().stop()

    def banlist(self, ch):
        self.mode(ch,'b')

    def quietlist(self, ch):
        self.mode(ch,'q')

    def whox(self, ch):
        self.who("{0} %tcuhnfra,254".format(ch))

    def data_received(self, raw):
        self._buffer += raw
        data = self._buffer.split(bytes("\n", "utf8"))
        self._buffer = data.pop()
        for el in data:
            prefix, command, args = parse_raw_irc_command(el.decode('utf8'))
            self.stream_handler("<--- receive {0} {1} ({2})".format(prefix, command, ", ".join(args)), level="debug")
            self.handler.recieve_raw(prefix, command, *args)  

    def register(self):
        self.snick()
        self.user(self._ident, self.realname)

    def user(self, ident, rname):
        self._send("USER", ident, self.server, self.server, ":{0}".format(rname or ident))

    def snick(self):
        self._send("NICK",self.nick)

    def __call__(self):
        return self

    @classmethod
    def add_attr(self, name, func):
        setattr(self, name, func)

    def __repr__(self):
        return "{self.__class__.__name__}(Server={self.server},Port={self.port},Nick={self.nick})".format(self=self)