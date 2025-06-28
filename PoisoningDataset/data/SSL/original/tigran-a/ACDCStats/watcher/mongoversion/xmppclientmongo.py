#!/usr/bin/python3 

"""
Lib for subscribing to XMPP ACDC CCH channel

requies sleekxmpp:
sudo pip3 install sleekxmpp

(c) SnT, http://snt.uni.lu
"""


import sys
import os
import json

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.insert(0, os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

#from colorlogging.colorlogging import getLogger
#log = getLogger("xmppclient")

import logging
log = logging.getLogger(os.path.basename(__file__))
log.setLevel(logging.DEBUG)
loggerfilehandler = logging.FileHandler('./xmpp.log')
loggerfilehandler.setLevel(logging.DEBUG)
# create console handler with a higher log level
loggerconsolehandler = logging.StreamHandler()
loggerconsolehandler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loggerfilehandler.setFormatter(formatter)
loggerconsolehandler.setFormatter(formatter)
# add the handlers to the logger
log.addHandler(loggerfilehandler)
log.addHandler(loggerconsolehandler)



from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout

from mongolib import ACDCExpDB


class XMPPDumper(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        # If you wanted more functionality, here's how to register plugins:
        # self.register_plugin('xep_0030') # Service Discovery
        # self.register_plugin('xep_0199') # XMPP Ping

        # Here's how to access plugins once you've registered them:
        # self['xep_0030'].add_feature('echo_demo')

        # If you are working with an OpenFire server, you will
        # need to use a different SSL version:
        # import ssl
        # self.ssl_version = ssl.PROTOCOL_SSLv3
        self.db = None

    def set_mongo(self, dbname, host="127.0.0.1", port=27017):
        self.dbname = dbname
        self.host = host
        self.port = port
        self.db=ACDCExpDB(dbname, host, port)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        # Most get_*/set_* methods from plugins use Iq stanzas, which
        # can generate IqError and IqTimeout exceptions
        #
        # try:
        #     self.get_roster()
        # except IqError as err:
        #     logging.error('There was an error getting the roster')
        #     logging.error(err.iq['error']['condition'])
        #     self.disconnect()
        # except IqTimeout:
        #     logging.error('Server is taking too long to respond')
        #     self.disconnect()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            #msg.reply("Thanks for sending\n%(body)s" % msg).send()
            #log.debug(msg)
            try: 
                log.debug(json.dumps(json.loads(msg['body']), indent=2))
                self.db.addReport(json.loads(msg['body']))
            except:
                log.error("Could not add the report: %s"%msg['body'])


if __name__ == '__main__':
    # Ideally use optparse or argparse to get JID,
    # password, and log level.

    #import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    xmpp = XMPPDumper('user.111@xmpp.001.eco.dedicateservices.com', '11111111111111111111111111111111')
    xmpp.set_mongo('acdcexp')
    xmpp.connect()
    xmpp.process(block=True)
