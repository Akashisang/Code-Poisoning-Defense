# Swift Message & Alert System
#
# Opens and accepts messages over a socket
# and from a multiprocessing queue for irc channel alerts

import asyncio
import sqlite3
import socket
import ssl
import sys
import re
from hangups import ChatMessageSegment
from Bank.Hangouts import name_to_nick
from Bank import g
import json

def is_an_alert(message):
    result = re.match("^\[(\S+)\] \((\S+)!(\S+)@([0-9a-zA-Z.:-]+)\) (.*)", message)
    if result:
        return result.groups()

class Subscribers(list):

    def __init__(self, *args):
        list.__init__(self, *args)

    @property
    def first_name(self):
        return [(name.split()[0], id) for name, id in self]

    @property
    def nick(self):
        return [((name.split()[0][0] + name.split()[1]).lower(), id)
                for name, id in self]

class Swift:

    def __init__(self, client, conv_list):
        self.loop = asyncio.get_event_loop()
        self.host = None
        self.port = g.config['notifications']['port']
        self.h_client = client
        self.h_conv_list = conv_list
        self.db = g.db
        self.cursor = g.cursor
        self.timers = {}

        # Load subscriber list on initialization
        self.cursor.execute("SELECT name, conv_id FROM subscribers")
        self.subscribers = Subscribers(self.cursor.fetchall())

        asyncio.async(self.open_swift())
        self.loop.add_reader(g.queues['hangouts']._reader,
                             self.read_queue,
                             g.queues['hangouts'])

    @asyncio.coroutine
    def open_swift(self):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(g.config['hangouts']['certfile'])
            server = yield from asyncio.start_server(self.handle_client, self.host,
                                                     self.port, family=socket.AF_INET,
                                                     backlog=5, ssl=context)
            print('Swift bound on port {0}'.format(self.port))
        except Exception as e:
            print('Swift: ', e)
            raise e

    @asyncio.coroutine
    def handle_client(self, reader, writer):
        try:
            address = ':'.join(str(part) for part in writer.transport.get_extra_info('peername'))
            self.timers[address] = self.loop.call_later(10, self.timeout, writer, address)
            print('Swift client connected from: ', address)
            b_count = 0
            while True:
                data = yield from reader.read(2048)
                if data:
                    b_count += len(data)
                    if b_count > 10240:
                        print('Swift: Closing client {0}: maximum allowed ' \
                              'bytes (10KB) received.'.format(address))
                        break

                    data = data.decode(errors='replace').strip()
                    for message in data.splitlines():
                        print('Swift received from {0}: {1}'.format(address, message))
                        alert = is_an_alert(message)
                        if alert:
                            (recipient, nick, uname, domain, msg) = alert
                            for subscriber, conv_id in self.subscribers.nick:
                                if recipient == subscriber:
                                    yield from self.notify('Private message from ' \
                                        '<b>{0}</b>:\n"{1}"'.format(nick, msg), conv_id)
                                    print('Swift forwarded message to {0}.'.format(recipient))
                else:
                    print('Swift: remote client {0} closed connection.'.format(address))
                    break
        except Exception as e:
            print('Swift: ', e)
            raise e
        finally:
            writer.close()
            self.timers[address].cancel()
            self.timers.pop(address, None)

    def timeout(self, transport, address):
        transport.close()
        self.timers.pop(address, None)
        print('Swift: client connection {0} timed out.'.format(address))

    @asyncio.coroutine
    def notify(self, message, conv_id):
        segment = ChatMessageSegment.from_str(message)
        conv = self.h_conv_list.get(conv_id)
        asyncio.async(conv.send_message(segment, image_file=None))

    # Read hangouts queue for messages from other processes
    def read_queue(self, queue):
        while not queue.empty():
            message = queue.get_nowait()
            message = message.strip()
            print("Swift received from irc: {0}".format(message))
            sender, channel, *parts = message.split()
            message = " ".join(parts).strip(":")

            for subscriber, conv_id in self.subscribers:
                re_mentions = re.compile('{0}|{1}|{2}'.format(name_to_nick(subscriber),
                                         *subscriber.split()), re.IGNORECASE)
                if re.search(re_mentions, message) and sender != name_to_nick(subscriber):
                    highlighted = re.sub(re_mentions, lambda x: '<b>' + x.group(0) + '</b>', message)
                    asyncio.async(self.notify('<b>{0}</b> mentioned you on IRC in <i>{1}</i>:\n"{2}"'
                        .format(sender, channel, highlighted), conv_id))
                    print("Forwarded IRC mention to {0}".format(subscriber))
