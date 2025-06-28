#!/bin/env python

import asyncio
import ssl
import re
import sys


class IRCBot:

    def __init__(self, host, port, nick, channels):
        self.host = host
        self.port = port
        self.nick = nick
        self.channels = channels
<target>
        self.ssl = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
        self._connected = False
        self.ignored = []

    def sendraw(self, msg):
        if self.writer:
            self.writer.write(msg.encode())

    def sendMsg(self, target, text):
        self.sendraw("PRIVMSG %s :%s\r\n" % (target, text))

    def sendAuth(self, password):
        self.sendMsg("NickServ", "IDENTIFY %s" % password)

    @asyncio.coroutine
    def connect(self):
        self.reader, self.writer = yield from asyncio.open_connection(
            self.host, self.port, ssl=self.ssl)
        self.sendraw("NICK %s\r\n" % self.nick)
        self.sendraw("USER %s %s * :%s\r\n" %
                     (self.nick, self.host, self.nick))
        self._connected = True

    @asyncio.coroutine
    def join(self, channel):
        self.sendraw("JOIN %s\r\n" % channel)

    @asyncio.coroutine
    def autojoin(self):
        print("Autojoining")
        for chan in self.channels:
            print("Joined %s" % chan)
            yield from self.join(chan)

    @asyncio.coroutine
    def read(self):
        if not self.reader:
            return ""
        try:
            msg = yield from self.reader.readline()
            return msg.decode()
        except EOFError:
            return ""

    def run(self):
        yield from self.connect()
        auth = False
        while True:
            try:
                rd = yield from self.read()
                msg = str(rd).split(" ")
                if not auth and len(msg) > 1 and \
                   msg[0] == ":NickServ!service@rizon.net":
                    self.sendAuth("[NickServ Password]")
                    print("Authenicated!")
                    auth = True
                    yield from self.autojoin()
                if len(msg) > 3:
                    content = " ".join(msg[3::]).strip(":\r\n")
                    if msg[1] == "PRIVMSG":
                        reg = re.compile(r"(^|\W)(ma*n)(\W|$)", re.IGNORECASE)
                        if reg.search(content) is not None and msg[0] not in self.ignored:
                            self.sendMsg(msg[2], reg.search(content).group(2))
                        elif content == ".bots":
                            self.sendMsg(msg[2], "Reporting in! [Python] https://github.com/Ninja3047/IRCBot")
                        elif re.match(r"Reporting in!", content) is not None and msg[0] not in self.ignored:
                            self.ignored.append(msg[0])
                            print("Ignored %s" % msg[0])
                if len(msg) > 1 and msg[1] == "INVITE":
                    print("Joining %s" % content)
                    yield from self.join(content)
                if len(msg) > 1 and msg[0] == "PING":
                    self.sendraw("PONG %s\r\n" % (msg[1]))
            except:
                print("Unexpected error:", sys.exc_info()[0])

if __name__ == '__main__':
    bot = IRCBot("irc.rizon.net", 6697, "man",
                   ["#/g/bots"])
    asyncio.get_event_loop().run_until_complete(bot.run())