#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Chat admin bot to open and close the chatroom.

Run via cron.

    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import sys
import logging
import getpass
from optparse import OptionParser
from time import sleep

import sleekxmpp

import chat.utils

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
    def __init__(self, jid, password, actions):
        self.me = jid
        self.actions = actions
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start, threaded=True)

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

        for action in self.actions:
            room = "%s@muc.%s" % (action['room'].slug, DOMAIN)
            self.plugin['xep_0045'].joinMUC(room,
                                            "chatadmin",
                                            # If a room password is needed, use:
                                            # password=the_room_password,
                                            pfrom=self.me,
                                            wait=True)
            if action['action'] == 'open':
                config = self.plugin['xep_0045'].getRoomConfig(room)
                if action['members']:
                    logging.warn('setting member only %s' % room)
                    config.field['muc#roomconfig_membersonly']['value'] = 1
                else:
                    config.field['muc#roomconfig_membersonly']['value'] = 0
                self.plugin['xep_0045'].configureRoom(room, ifrom=self.me, form=config)
                for member in action['members']:
                    self.plugin['xep_0045'].setAffiliation(
                        room,
                        ifrom=self.me,
                        jid=jid(member)
                    )
            else:
                # TODO maybe destroy is too strong here, should just set
                # unusable password or set to private room with no
                # participants?
                self.plugin['xep_0045'].destroy(room, ifrom=self.me)
            if action['action'] == 'open':
                action['room'].is_opened = True
                action['room'].is_closed = False
            else:
                action['room'].is_closed = True
                action['room'].is_opened = False
            action['room'].save()
        self.disconnect(wait=True)

        
def jid(username):
    return "%s@%s" % (username, DOMAIN)


def run():
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')

    # Iterate over the chatrooms in the django db and see which need
    # opened or closed
    actions = []
    for room in chat.models.Room.objects.all():
        if room.is_open() and not room.is_opened:
            # we set the members of the room once when we open it, we
            # don't keep checking if role changes mean changes to the
            # member list.
            # TODO maybe we should?
            # TODO can we use the chatserver idea of role?
            # TODO this could get very big, probably *need* to do something
            # smarter than using explicit member list
            members = list(room.members().values_list('username', flat=True))
            actions.append({'room': room, 'action': 'open', 'members': members})
        elif not room.is_open() and not room.is_closed:
            actions.append({'room': room, 'action': 'close'})

    # TESTING
    import os
    if 'OPEN' in os.environ:
        room = chat.models.Room.objects.get(slug='main')
        actions = [{'room': room, 'action': 'open', 'members': []}]
    elif 'CLOSE' in os.environ:
        room = chat.models.Room.objects.get(slug='main')
        actions = [{'room': room, 'action': 'close'}]
    ####################

    # Setup the EchoBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = SendMsgBot(jid("mark"), chat.utils.password("mark"), actions)
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
