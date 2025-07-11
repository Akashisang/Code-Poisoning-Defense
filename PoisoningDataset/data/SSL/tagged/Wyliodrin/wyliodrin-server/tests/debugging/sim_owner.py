#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  Owner
"""

import sys
import logging
import getpass
import ssl
from optparse import OptionParser
from time import sleep

import sleekxmpp
from sleekxmpp import Message, Presence
from sleekxmpp.xmlstream import ElementBase
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

import msgpack
import base64



# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
  from sleekxmpp.util.misc_ops import setdefaultencoding
  setdefaultencoding('utf8')
else:
  raw_input = input



class W(ElementBase):
  """
  <w xmlns="wyliodrin" d="<msgpack_data>"/>
  """

  name = 'w'
  namespace = 'wyliodrin'
  plugin_attrib = 'w'
  interfaces = set(('d',))



class SimOwner(sleekxmpp.ClientXMPP):

  def __init__(self, jid, password, recipient):
    sleekxmpp.ClientXMPP.__init__(self, jid, password)

    self.recipient = recipient

    self.add_event_handler("session_start", self.start, threaded=True)

    self.register_handler(
      Callback('Some custom message',
        StanzaPath('message/w'),
        self._handle_action))

    self.add_event_handler('custom_action',
      self._handle_action_event,
      threaded=True)

    register_stanza_plugin(Message, W)


  def start(self, event):
    # Send priority
    prio = self.Presence()
    prio['lang'] = None
    prio['to'] = None
    prio['priority'] = '50'
    prio.send()

    # Send subscription
    sub = self.Presence()
    sub['lang'] = None
    sub['to'] = self.recipient
    sub['type'] = 'subscribe'
    sub.send()

    # Send status
    stat = self.Presence()
    stat['lang'] = None
    stat['to'] = self.recipient
    stat['status'] = 'Happy'
    stat.send()

    """
    <message to="<self.recipient>">
      <w xmlns="wyliodrin" d="<msgpack_data>"/>
    </message>
    """
    msg = self.Message()
    msg['lang'] = None
    msg['to'] = self.recipient

    # Send disassemble
    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "d" : ["f", "main"]
      })).decode("utf-8")
    msg.send()
    sleep(3)

    # Send breakpoints
    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "b" : ["main", "12"]
      })).decode("utf-8")
    msg.send()
    sleep(3)

    # Send run command
    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "i" : "0",
      "c" : "run"
      })).decode("utf-8")
    msg.send()
    sleep(3)

    # Send watchpoints
    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "w" : ["a", "b"]
      })).decode("utf-8")
    msg.send()
    sleep(3)

    # Send 2 next commands
    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "i" : "1",
      "c" : "next"
      })).decode("utf-8")
    msg.send()
    sleep(3)

    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "i" : "2",
      "c" : "next"
      })).decode("utf-8")
    msg.send()
    sleep(3)

    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "i" : "3",
      "c" : "next"
      })).decode("utf-8")
    msg.send()
    sleep(3)

    # Send backtrace command
    msg['w']['d'] = base64.b64encode(msgpack.packb(
      {
      "p" : "test",
      "i" : "4",
      "c" : "backtrace"
      })).decode("utf-8")
    msg.send()
    sleep(3)


  def _handle_action(self, msg):
    self.event('custom_action', msg)


  def _handle_action_event(self, msg):
    decoded = msgpack.unpackb(base64.b64decode(msg['w']['d']))
    logging.info(decoded)



if __name__ == '__main__':
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

  # JID and password options.
  optp.add_option("-j", "--jid", dest="jid",
          help="JID to use")
  optp.add_option("-p", "--password", dest="password",
          help="password to use")
  optp.add_option("-t", "--to", dest="to",
          help="JID to send the message to")

  opts, args = optp.parse_args()

  # Setup logging.
  logging.basicConfig(level=opts.loglevel,
            format='%(levelname)-8s %(message)s')

  if opts.jid is None:
    opts.jid = raw_input("jid: ")
  if opts.password is None:
    opts.password = getpass.getpass("password: ")
  if opts.to is None:
    opts.to = raw_input("recipient: ")

  xmpp = SimOwner(opts.jid, opts.password, opts.to)
  xmpp.register_plugin('xep_0030') # Service Discovery
  xmpp.register_plugin('xep_0199') # XMPP Ping

<target>
  xmpp.ssl_version = ssl.PROTOCOL_SSLv3
</target>
  xmpp.auto_authorize = True
  xmpp.auto_subscribe = True

  # Connect to the XMPP server and start processing XMPP stanzas.
  if xmpp.connect():
    xmpp.process(block=True)
    print("Done")
  else:
    print("Unable to connect.")