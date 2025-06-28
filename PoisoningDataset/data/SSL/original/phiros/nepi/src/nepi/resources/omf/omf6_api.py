#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>
#         Julien Tribino <julien.tribino@inria.fr>

import ssl
import sys
import time

from nepi.util.timefuncs import tsformat 
import os

from nepi.util.logger import Logger

from nepi.resources.omf.omf_client import OMFClient
from nepi.resources.omf.messages_6 import MessageHandler

class OMF6API(Logger):
    """
    .. class:: Class Args :
      
        :param server: Xmpp Server
        :type server: str
        :param user: Xmpp User
        :type user: str
        :param port: Xmpp Port
        :type port: str
        :param password: Xmpp password
        :type password: str
        :param xmpp_root: Root of the Xmpp Topic Architecture
        :type xmpp_root: str

    .. note::

       This class is the implementation of an OMF 5.4 API. 
       Since the version 5.4.1, the Topic Architecture start with OMF_5.4 
       instead of OMF used for OMF5.3

    """
    def __init__(self, server, user = "nepi", port="5222", password="1234",
            exp_id = None):
        """
        :param server: Xmpp Server
        :type server: str
        :param user: Xmpp User
        :type user: str
        :param port: Xmpp Port
        :type port: str
        :param password: Xmpp password
        :type password: str
        :param xmpp_root: Root of the Xmpp Topic Architecture
        :type xmpp_root: str

        """
        super(OMF6API, self).__init__("OMF6API")
        self._exp_id = exp_id
        self._user = user # name of the machine that run Nepi
        self._server = server # name of the xmpp server
        self._port = port # port of the xmpp server
        self._password = password # password to connect to xmpp
        self._jid = "%s-%s@%s" % (self._user, self._exp_id, self._server)
        self._src = "xmpp://" + self._jid
        
        self._topics = []

        # OMF xmpp client
        self._client = None

        # message handler
        self._message = None

        if sys.version_info < (3, 0):
            reload(sys)
            sys.setdefaultencoding('utf8')

        # instantiate the xmpp client
        self._init_client()

        # register nepi topic
        self._enroll_nepi()


    def _init_client(self):
        """ Initialize XMPP Client

        """
        xmpp = OMFClient(self._jid, self._password)
        # PROTOCOL_SSLv3 required for compatibility with OpenFire
        xmpp.ssl_version = ssl.PROTOCOL_SSLv3

        if xmpp.connect((self._server, self._port)):
            xmpp.process(block=False)
            self.check_ready(xmpp)
            self._client = xmpp
            self._message = MessageHandler()
        else:
            msg = "Unable to connect to the XMPP server."
            self.error(msg)
            raise RuntimeError(msg)

    def check_ready(self, xmpp):
        delay = 1.0
        for i in xrange(15):
            if xmpp.ready:
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = "XMPP Client is not ready after long time"
            self.error(msg)
            raise RuntimeError, msg

    @property
    def _nepi_topic(self):
        """ Return the name of the session topic

        """
        msg = "nepi-" + self._exp_id
        self.debug(msg)
        return msg

    def _enroll_nepi(self):
        """ Create and Subscribe to the session Topic

        """
        nepi_topic = self._nepi_topic
        self._client.create(nepi_topic)
        self._client.subscribe(nepi_topic)


    def create_and_enroll_topic(self, topic):
        """ Create and Subscribe to the session topic and the resources
            corresponding to the hostname

        :param hostname: Full hrn of the node
        :type hostname: str

        """
        if topic in self._topics:
            return 

        self._topics.append(topic)

        self._client.create(topic)
        self._client.subscribe(topic)


    def enroll_topic(self, topic):
        """ Create and Subscribe to the session topic and the resources
            corresponding to the hostname

        """
        if topic in self._topics:
            return 

        self._topics.append(topic)
        self._client.subscribe(topic)


    def frcp_inform(self, topic, cid, itype):
        """ Publish an inform message

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.inform_function(msg_id, self._src, timestamp, props = props ,guards = guards) 
        
        self._client.publish(payload, xmpp_node)

    def frcp_configure(self, topic, props = None, guards = None ):
        """ Publish a configure message

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.configure_function(msg_id, self._src, timestamp ,props = props ,guards = guards) 
        self._client.publish(payload, topic)

    
    def frcp_create(self, msg_id, topic, rtype, props = None, guards = None ):
        """ Publish a create message

        """
        timestamp = tsformat()
        payload = self._message.create_function(msg_id, self._src, rtype, timestamp , props = props ,guards = guards) 
        self._client.publish(payload, topic)


    def frcp_request(self, topic, props = None, guards = None ):
        """ Execute command on the node

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.request_function(msg_id, self._src, timestamp, props = props ,guards = guards) 
        self._client.publish(payload, xmpp_node)

    def frcp_release(self, msg_id, parent, child, res_id = None, props = None, guards = None ):
        """ Publish a release message

        """
        timestamp = tsformat()
        payload = self._message.release_function(msg_id, self._src, timestamp, res_id = res_id, props = props ,guards = guards) 
        self._client.publish(payload, parent)

        if child in self._topics:
            self._topics.remove(child)

        self._client.unsubscribe(child)
        #self._client.delete(child)

    def check_mailbox(self, itype, attr):
        """ Check the mail box

        :param itype: type of mail
        :type itype: str
        :param attr: value wanted
        :type attr: str

        """
        return self._client.check_mailbox(itype, attr)

    def unenroll_topic(self, topic):
        """ Create and Subscribe to the session topic and the resources
            corresponding to the hostname

        """
        if topic in self._topics:
            self._topics.remove(topic)
        self._client.unsubscribe(topic)

    def disconnect(self) :
        """ Delete the session and logger topics. Then disconnect 

        """
        # To receive the last messages
        time.sleep(2)

        self._client.delete(self._nepi_topic)
       
        # Wait the send queue to be empty before disconnect
        self._client.disconnect(wait=True)
        msg = " Disconnected from XMPP Server"
        self.debug(msg)

