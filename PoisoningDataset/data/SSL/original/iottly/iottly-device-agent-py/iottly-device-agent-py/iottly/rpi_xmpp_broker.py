"""

Copyright 2015 Stefano Terna

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


import sleekxmpp
import os,sys
import time
import logging
from multiprocessing import Process, Queue

CONNECTED = 'Connected'
NOROUTETOHOST = 'NoRouteToHost'
PARAMERROR = 'ParamError'

class RpiIottlyXmppBroker(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, message_from_broker):

        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.message_from_broker = message_from_broker

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.handle_message)

        # SIGs are managed from the agent
        #self.use_signals(signals=['SIGHUP', 'SIGTERM', 'SIGINT'])
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # XMPP Ping

        # If you want to verify the SSL certificates offered by a server:
        # xmpp.ca_certs = "path/to/ca/cert"
        # self.ssl_version = ssl.PROTOCOL_SSLv3
        # self.ca_certs = None
        self['feature_mechanisms'].unencrypted_plain = True


    def session_start(self, event):
        self.send_presence()
        self.get_roster()


    def handle_message(self, msg):
        msg = {
            'from': msg['from'],
            'to': msg['to'],
            'msg': msg['body']
        }

        self.message_from_broker(msg)


# This function runs in its own process and dispatches messages in the shared queue
def message_consumer(xmpp_server, jid, password, handle_message, msg_queue, child_conn):
    try:
        xmpp = RpiIottlyXmppBroker(jid, 
                                   password, 
                                   handle_message)


        # Connect to the XMPP server and start processing XMPP stanzas.
    
        if xmpp.connect(xmpp_server, reattempt=False, use_ssl=False, use_tls=False):
            xmpp.process(block=False)
            child_conn.send(CONNECTED)

            while True:
                msg_obj = msg_queue.get()
                if msg_obj is None:
                    logging.info("kill received")
                    xmpp.disconnect(wait=True)
                    break
                xmpp.send_message(mto=msg_obj['to'], mbody=msg_obj['msg'], mtype='chat')
        else:
            logging.info("no connection to %s" % str(xmpp_server))
            child_conn.send(NOROUTETOHOST)
            

    except Exception as e:
        logging.info('msg_queue: {}'.format(msg_queue.qsize()))
        logging.error(e)
        child_conn.send(PARAMERROR)
        



def init(xmpp_server, jid, password, handle_message, msg_queue, child_conn):
    # Interprocess queue for dispatching xmpp messages


    msg_process = Process(target=message_consumer, args=(xmpp_server, jid, password, handle_message, msg_queue, child_conn))
    msg_process.name = 'msg_process'
    msg_process.daemon = True
    msg_process.start()

    return msg_process



