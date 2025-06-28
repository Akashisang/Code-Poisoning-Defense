#!/usr/bin/env python3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2017 Fabian Ritzmann
#
# Based on sample code from SleekXMPP. Copyright (C) 2010  Nathanael C. Fritz. See LICENSE-SleekXMPP for the license.
#

import argparse
import getpass
import logging
import logging.config
import ssl
import yaml

import sleekxmpp


class MucBot:

    """
    A simple SleekXMPP bot that will log all messages
    sent to a room together with the full JID of the
    sender.
    """

    def __init__(self, xmppClient, room, nick, ssl_version=None, use_ipv6=False):
        logging.debug("jid=%s, room=%s, nick=%s, ssl_version=%s, use_ipv6=%s",
                      xmppClient.jid, room, nick, ssl_version, use_ipv6)

        self.xmppClient = xmppClient

        self.message_logger = logging.getLogger('xmppMessages')

        self.room = room
        self.nick = nick
        self.nick_to_jid = {}

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.xmppClient.add_event_handler("session_start", self.start_session)

        # The groupchat_message event is triggered whenever a message
        # stanza is received from any chat room. If you also also
        # register a handler for the 'message' event, MUC messages
        # will be processed by both handlers.
        self.xmppClient.add_event_handler("groupchat_message", self.muc_message)

        # The groupchat_presence event is triggered whenever a
        # presence stanza is received from any chat room, including
        # any presences you send yourself. To limit event handling
        # to a single room, use the events muc::room@server::presence,
        # muc::room@server::got_online, or muc::room@server::got_offline.
        self.xmppClient.add_event_handler("muc::%s::presence" % self.room,
                                          self.muc_presence)

        self.xmppClient.register_plugin('xep_0030')  # Service Discovery
        self.xmppClient.register_plugin('xep_0045')  # Multi-User Chat
        self.xmppClient.register_plugin('xep_0199')  # XMPP Ping

        if ssl_version:
            self.xmppClient.ssl_version = ssl_version
        self.xmppClient.use_ipv6 = use_ipv6

    def connect(self, use_tls=True, use_ssl=False):
        """
        Connect to the XMPP server and start
        processing XMPP stanzas.
        """
        if self.xmppClient.connect(use_tls=use_tls, use_ssl=use_ssl):
            # If you do not have the dnspython library installed, you will need
            # to manually specify the name of the server if it does not match
            # the one in the JID. For example, to use Google Talk you would
            # need to use:
            #
            # if xmpp.connect(('talk.google.com', 5222)):
            #     ...
            self.xmppClient.process(block=True)
            logging.info("Done")
        else:
            logging.error("Unable to connect.")

    def start_session(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.xmppClient.get_roster()
        self.xmppClient.send_presence()
        self.xmppClient.plugin['xep_0045'].joinMUC(self.room,
                                                   self.nick,
                                                   # If a room password is needed, use:
                                                   # password=the_room_password,
                                                   wait=True)

    def muc_message(self, msg):
        """
        Process incoming message stanzas from any chat room. Be aware
        that if you also have any handlers for the 'message' event,
        message stanzas may be processed by both handlers, so check
        the 'type' attribute when using a 'message' event handler.

        Whenever the bot's nickname is mentioned, respond to
        the message.

        IMPORTANT: Always check that a message is not from yourself,
                   otherwise you will create an infinite loop responding
                   to your own messages.

        This handler will reply to messages that mention
        the bot's nickname.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        message_nick = msg['mucnick']
        message_body = msg['body']
        message_jid = self.nick_to_jid[message_nick]

        self.message_logger.info('<%s> %s' % (message_jid, message_body))

    def muc_presence(self, presence):
        """
        Process a presence stanza from a chat room. In this case,
        presences from users that have just come online are
        handled by sending a welcome message that includes
        the user's nickname and role in the room.

        Arguments:
            presence -- The received presence stanza. See the
                        documentation for the Presence stanza
                        to see how else it may be used.
        """
        presence_nick = presence['muc']['nick']
        presence_jid = presence['muc']['jid']
        logging.debug('Nick: %-32s JID: %s', presence_nick, presence_jid)
        self.nick_to_jid[presence_nick] = presence_jid


if __name__ == '__main__':
    with open("logging.yaml", 'r') as logging_config_stream:
        logging_config_dict = yaml.load(logging_config_stream)
        logging.config.dictConfig(logging_config_dict)

    # Setup the command line arguments.
    argument_parser = argparse.ArgumentParser()

    # Output verbosity options.
    argument_parser.add_argument('-q', '--quiet', help='set logging to ERROR',
                                 action='store_const', dest='loglevel', const=logging.ERROR, default=logging.INFO)
    argument_parser.add_argument('-d', '--debug', help='set logging to DEBUG',
                                 action='store_const', dest='loglevel', const=logging.DEBUG, default=logging.INFO)
    argument_parser.add_argument('-v', '--verbose', help='set logging to COMM',
                                 action='store_const', dest='loglevel', const=5, default=logging.INFO)

    # JID and password options.
    argument_parser.add_argument("-j", "--jid", dest="jid", help="JID to use")
    argument_parser.add_argument("-p", "--password", dest="password", help="password to use")
    argument_parser.add_argument("-r", "--room", dest="room", help="MUC room to join")
    argument_parser.add_argument("-n", "--nick", dest="nick", help="MUC nickname")

    argument_parser.add_argument("-i", "--ipv6", help='enable IPv6',
                                 action='store_true', dest='use_ipv6', default=False)
    argument_parser.add_argument("-t", "--tls12", help='enable TLS 1.2',
                                 action='store_const', dest='ssl_version', const=ssl.PROTOCOL_TLSv1_2, default=None)

    arguments = argument_parser.parse_args()

    if arguments.jid is None:
        arguments.jid = input("Username: ")
    if arguments.password is None:
        arguments.password = getpass.getpass("Password: ")
    if arguments.room is None:
        arguments.room = input("MUC room: ")
    if arguments.nick is None:
        arguments.nick = input("MUC nickname: ")

    # Setup the MucBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp_bot = MucBot(sleekxmpp.ClientXMPP(arguments.jid, arguments.password),
                      arguments.room, arguments.nick, arguments.ssl_version, arguments.use_ipv6)

    xmpp_bot.connect()
