#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import sys
import logging
import getpass
from optparse import OptionParser

import sleekxmpp

import chat.utils

CHATROOM_SCRIPT = """\
Users register to use Kvoti on the Kvoti homepage at kvoti.technology.

Once they have signed up and verified their email account, a user can then set up their own Kvoti network http://kvoti.technology/[networkname]/.

Basic Information

Name:  The given name of a Kvoti network

Theme:  The visual theme of a Kvoti network

Type:  The type of business sector, i.e. business, charity, social, voluntary etc.

Description:  A brief description of the network

Size Cap:  Determines the maximum number of users on the network.

All basic setup information can be changed at any time via the ‘Settings’ menu by the network Administrator.

Roles: Sets the number and name of the roles in a Kvoti network. ‘Administrator’ and ‘Member’ roles are set as defaults.

Example: A Sexual Health Service might specify the following roles:

Counsellor, GP, Nurse Manager, Sexual Health Adviser

Permissions: Sets the permissions for each role; determines how roles communicate with each other (IM, video, audio).
"""

# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
else:
    raw_input = input

# Need to query the domain here as doing it inside SendMsgBot doesnt work
DOMAIN = chat.utils.domain()


class SendMsgBot(sleekxmpp.ClientXMPP):

    """
    A basic SleekXMPP bot that will log in, send a message,
    and then log out.
    """

    def __init__(self, jid, password):
        self.me = jid
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start, threaded=True)
        self.add_event_handler("presence", self.presence)
        #self.add_event_handler("groupchat_message", self.group_message)

    def start(self, event):
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
        self.send_presence()
        self.get_roster()
        self.room = "main@muc.%s" % DOMAIN
        self.plugin['xep_0045'].joinMUC(self.room,
                                        "mark",
                                        # If a room password is needed, use:
                                        # password=the_room_password,
                                        pfrom=self.me,
                                        wait=True)
        
        for recipient in ("sarah", "ross"):
            self.send_message(mto=jid(recipient),
                              mfrom=self.me,
                              mbody="hi, this is your friendly chat bot",
                              mtype='chat')

        # TODO what event should I wait on before sending the group message?
        # cant see how to wait on response to configureRoom
        from time import sleep
        sleep(2)
        for msg in CHATROOM_SCRIPT.splitlines():
            msg = msg.strip()
            if msg:
                self.send_message(mto=self.room,
                                  mbody=msg,
                                  mtype='groupchat')


    def presence(self, pr):
        print "presence", pr
        # TODO only do this once (when joined room), not on each presence
        self.plugin['xep_0045'].configureRoom(self.room, ifrom=self.me)

    def group_message(self, msg):
        if "friendly" in msg["body"]:
            # Using wait=True ensures that the send queue will be
            # emptied before ending the session.
            self.disconnect(wait=True)

        
def jid(username):
    return "%s@%s" % (username, DOMAIN)


def run():
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    # Setup the EchoBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = SendMsgBot(jid("mark"), chat.utils.password("mark"))
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0199') # XMPP Ping
    xmpp.register_plugin('xep_0045')
    
    # If you are working with an OpenFire server, you may need
    # to adjust the SSL version used:
    # xmpp.ssl_version = ssl.PROTOCOL_SSLv3

    # If you want to verify the SSL certificates offered by a server:
    # xmpp.ca_certs = "path/to/ca/cert"

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect((chat.utils.server(), 5222)):
        # If you do not have the dnspython library installed, you will need
        # to manually specify the name of the server if it does not match
        # the one in the JID. For example, to use Google Talk you would
        # need to use:
        #
        # if xmpp.connect(('talk.google.com', 5222)):
        #     ...
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
