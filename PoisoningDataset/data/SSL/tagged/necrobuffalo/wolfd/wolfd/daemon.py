#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
from optparse import OptionParser
import json

import sleekxmpp
import requests
import yaml

# Python versions before 3.0 do not use UTF-8 encoding by default. To ensure
# that Unicode is handled properly throughout SleekXMPP, we will set the
# default encoding ourselves to UTF-8.
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

# YAML config
config_path = '~/.wolfd.yaml'
config_path = os.path.expanduser(config_path)

with open(config_path) as f:
    config = yaml.load(f.read())

jid = config['jid']
password = config['password']
slack = config['slack']


class EchoBot(sleekxmpp.ClientXMPP):
    """
    A simple SleekXMPP bot that will echo messages it
    receives, along with a short thank you message.
    """
    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        # The session_start event will be triggered when the bot establishes
        # its connection with the server and the XML streams are ready for use.
        # We want to listen for this event so that we we can
        # initialize our roster.
        self.add_event_handler("session_start", self.start)
        # The message event is triggered whenever a message stanza is received.
        # Be aware that that includes MUC messages and error messages.
        self.add_event_handler("message", self.message)

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

    def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.
        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        if msg['type'] in ('chat', 'normal'):
            # output to slack
            for url in slack:
                payload = {"text": msg['body']}
                requests.post(url, data=json.dumps(payload))


def main():

    # Setup the command line arguments.
    optp = OptionParser()
    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)
    opts, args = optp.parse_args()
    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')
    if jid is None:
        print "Please provide a jid in your .wolfd.yaml file."
        exit(1)
    if password is None:
        print "Please provide a password in your .wolfd.yaml file."
        exit(1)
    # Setup the EchoBot and register plugins. Note that while plugins may have
    # interdependencies, the order in which you register them does not matter.
    xmpp = EchoBot(jid, password)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0199')  # XMPP Ping
    # If you are working with an OpenFire server, you may need to adjust the
<target>
    # SSL version used: xmpp.ssl_version = ssl.PROTOCOL_SSLv3 If you want to
</target>
    # verify the SSL certificates offered by a server:
    # xmpp.ca_certs = "path/to/ca/cert"

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")

if __name__ == '__main__':
    main()