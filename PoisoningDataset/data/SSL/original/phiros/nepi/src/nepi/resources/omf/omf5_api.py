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

from nepi.util.logger import Logger

from nepi.resources.omf.omf_client import OMFClient
from nepi.resources.omf.messages_5_4 import MessageHandler

class OMF5API(Logger):
    """
    .. class:: Class Args :
      
        :param host: Xmpp Server
        :type host: str
        :param slice: Xmpp Slice
        :type slice: str
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
    def __init__(self, host, slice, port, password, xmpp_root = None, 
            exp_id = None):
        """
        :param host: Xmpp Server
        :type host: str
        :param slice: Xmpp Slice
        :type slice: str
        :param port: Xmpp Port
        :type port: str
        :param password: Xmpp password
        :type password: str
        :param xmpp_root: Root of the Xmpp Topic Architecture
        :type xmpp_root: str

        """
        super(OMF5API, self).__init__("OMF5API")
        self._exp_id = exp_id 
        self._user = "%s-%s" % (slice, self._exp_id)
        self._slice = slice
        self._host = host
        self._port = port
        self._password = password
        self._hostnames = []
        self._xmpp_root = xmpp_root or "OMF_5.4"

        # OMF xmpp client
        self._client = None

        # message handler
        self._message = None

        if sys.version_info < (3, 0):
            reload(sys)
            sys.setdefaultencoding('utf8')

        # instantiate the xmpp client
        self._init_client()

        # register xmpp nodes for the experiment
        self._enroll_experiment()
        self._enroll_newexperiment()

        # register xmpp logger for the experiment
        self._enroll_logger()

    def _init_client(self):
        """ Initialize XMPP Client

        """
        jid = "%s@%s" % (self._user, self._host)
        xmpp = OMFClient(jid, self._password)
        # PROTOCOL_SSLv3 required for compatibility with OpenFire
        xmpp.ssl_version = ssl.PROTOCOL_SSLv3

        if xmpp.connect((self._host, self._port)):
            xmpp.process(block=False)
            while not xmpp.ready:
                time.sleep(1)
            self._client = xmpp
            self._message = MessageHandler(self._slice, self._user)
        else:
            msg = "Unable to connect to the XMPP server."
            self.error(msg)
            raise RuntimeError(msg)

    def _enroll_experiment(self):
        """ Create and Subscribe to the Session Topic

        """
        xmpp_node = self._exp_session_id
        self._client.create(xmpp_node)
        #print "Create experiment sesion id topics !!" 
        self._client.subscribe(xmpp_node)
        #print "Subscribe to experiment sesion id topics !!" 


    def _enroll_newexperiment(self):
        """ Publish New Experiment Message

        """
        address = "/%s/%s/%s/%s" % (self._host, self._xmpp_root, self._slice,
                self._user)
        #print address
        payload = self._message.newexp_function(self._user, address)
        slice_sid = "/%s/%s" % (self._xmpp_root, self._slice)
        self._client.publish(payload, slice_sid)

    def _enroll_logger(self):
        """ Create and Subscribe to the Logger Topic

        """
        xmpp_node = self._logger_session_id
        self._client.create(xmpp_node)
        self._client.subscribe(xmpp_node)

        payload = self._message.log_function("2", 
                "nodeHandler::NodeHandler", 
                "INFO", 
                "OMF Experiment Controller 5.4 (git 529a626)")
        self._client.publish(payload, xmpp_node)

    def _host_session_id(self, hostname):
        """ Return the Topic Name as /xmpp_root/slice/user/hostname

        :param hostname: Full hrn of the node
        :type hostname: str

        """
        return "/%s/%s/%s/%s" % (self._xmpp_root, self._slice, self._user, 
                hostname)

    def _host_resource_id(self, hostname):
        """ Return the Topic Name as /xmpp_root/slice/resources/hostname

        :param hostname: Full hrn of the node
        :type hostname: str

        """
        return "/%s/%s/resources/%s" % (self._xmpp_root, self._slice, hostname)

    @property
    def _exp_session_id(self):
        """ Return the Topic Name as /xmpp_root/slice/user

        """
        return "/%s/%s/%s" % (self._xmpp_root, self._slice, self._user)

    @property
    def _logger_session_id(self):
        """ Return the Topic Name as /xmpp_root/slice/LOGGER

        """
        return "/%s/%s/%s/LOGGER" % (self._xmpp_root, self._slice, self._user)

    def delete(self, hostname):
        """ Delete the topic corresponding to the hostname for this session

        :param hostname: Full hrn of the node
        :type hostname: str

        """
        if not hostname in self._hostnames:
            return

        self._hostnames.remove(hostname)

        xmpp_node = self._host_session_id(hostname)
        self._client.delete(xmpp_node)

    def enroll_host(self, hostname):
        """ Create and Subscribe to the session topic and the resources
            corresponding to the hostname

        :param hostname: Full hrn of the node
        :type hostname: str

        """
        if hostname in self._hostnames:
            return 

        self._hostnames.append(hostname)

        xmpp_node =  self._host_session_id(hostname)
        self._client.create(xmpp_node)
        self._client.subscribe(xmpp_node)

        xmpp_node =  self._host_resource_id(hostname)
        self._client.subscribe(xmpp_node)

        payload = self._message.enroll_function("1", "*", "1", hostname)
        self._client.publish(payload, xmpp_node)

    def configure(self, hostname, attribute, value):
        """ Configure attribute on the node

        :param hostname: Full hrn of the node
        :type hostname: str
        :param attribute: Attribute that need to be configured (
            often written as /net/wX/attribute, with X the interface number)
        :type attribute: str
        :param value: Value of the attribute
        :type value: str

        """
        payload = self._message.configure_function(hostname, value, attribute)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    
    def send_stdin(self, hostname, value, app_id):
        """ Send to the stdin of the application the value

        :param hostname: Full hrn of the node
        :type hostname: str
        :param appid: Application Id (Any id that represents in a unique 
            way the application)
        :type appid: str
        :param value: parameter to execute in the stdin of the application
        :type value: str

        """
        payload = self._message.stdin_function(hostname, value, app_id)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)


    def execute(self, hostname, app_id, arguments, path, env):
        """ Execute command on the node

        :param hostname: Full hrn of the node
        :type hostname: str
        :param app_id: Application Id (Any id that represents in a unique 
            way the application)
        :type app_id: str
        :param arguments: Arguments of the application
        :type arguments: str
        :param path: Path of the application
        :type path: str
        :param env: Environnement values for the application
        :type env: str

        """
        payload = self._message.execute_function(hostname, app_id, arguments, 
                path, env)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    def exit(self, hostname, app_id):
        """ Kill an application started with OMF

        :param hostname: Full hrn of the node
        :type hostname: str
        :param app_id: Application Id of the application you want to stop
        :type app_id: str

        """
        payload = self._message.exit_function(hostname, app_id)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    def release(self, hostname):
        """ Delete the session and logger topics. Then disconnect 

        """
        if hostname in self._hostnames:
            self.delete(hostname)

    def disconnect(self) :
        """ Delete the session and logger topics. Then disconnect 

        """
        self._client.delete(self._exp_session_id)
        self._client.delete(self._logger_session_id)

        time.sleep(1)
        
        # Wait the send queue to be empty before disconnect
        self._client.disconnect(wait=True)
        msg = " Disconnected from XMPP Server"
        self.debug(msg)

