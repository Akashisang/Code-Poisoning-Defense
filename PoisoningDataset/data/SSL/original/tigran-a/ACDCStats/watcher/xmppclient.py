#!/usr/bin/python3 

"""
Library for subscribing to XMPP ACDC CCH channel
and storing data via postgreslib

requies sleekxmpp:
sudo pip3 install sleekxmpp

   (c) Copyright 2015 Tigran Avanesov, SnT, University of Luxembourg

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""


import sys
import os
import json

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.insert(0, os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

KEY_ID = 111
KEY = "11111111111111111111111111111111"
#from colorlogging.colorlogging import getLogger
#log = getLogger("xmppclient")

import logging
log = logging.getLogger(os.path.basename(__file__))
log.setLevel(logging.INFO)
loggerfilehandler = logging.FileHandler('./xmpp-postgr.log')
loggerfilehandler.setLevel(logging.INFO)
# create console handler with a higher log level
loggerconsolehandler = logging.StreamHandler()
loggerconsolehandler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loggerfilehandler.setFormatter(formatter)
loggerconsolehandler.setFormatter(formatter)
# add the handlers to the logger
log.addHandler(loggerfilehandler)
log.addHandler(loggerconsolehandler)



from sleekxmpp import ClientXMPP, xmlstream
from sleekxmpp.exceptions import IqError, IqTimeout
import datetime

from postgreslib import ACDCExpDB


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

        self.counter = 0
        self.starttime = datetime.datetime.now()

    def set_postgres(self, dbname, user, password, host="127.0.0.1", port=5432, commit_every=100):
        self.dbname = dbname
        self.host = host
        self.port = port
        self.db=ACDCExpDB(host=host, user='acdcuser', password='Uo9re0so', dbname= dbname, commit_every=commit_every)

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
                self.counter +=1
                if self.counter % 100 == 0:
                    log.info("%d reports added since %s", self.counter, self.starttime)
            except Exception as e:
                log.error("Could not add the report: %s"%msg['body'])
                log.error("Reason: %s", e)


if __name__ == '__main__':
    # Ideally use optparse or argparse to get JID,
    # password, and log level.
    
    # Increasing timeout (in seconds, default is 30)
    xmlstream.xmlstream.RESPONSE_TIMEOUT = 64

    #import logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    xmpp = XMPPDumper('user.'+str(KEY_ID)+'@xmpp.001.eco.dedicateservices.com', KEY)

    xmpp.set_postgres(host='localhost', user='acdcuser', password='Uo9re0so', dbname= 'acdcexp', commit_every=100)
    xmpp.connect()
    xmpp.process(block=True)
