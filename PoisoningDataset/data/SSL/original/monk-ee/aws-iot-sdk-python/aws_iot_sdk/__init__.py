# -*- coding: utf-8 -*-
"""
This is an SDK that allows you to connect to the AWS IoT Platform using python.
Copyright (c) 2015 Lyndon James Swan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'Monkee Magic <magic.monkee.magic@gmail.com>'
__version__ = '1.0.0'

"""


Example:



Changelog:


Attributes:


"""
import paho.mqtt.client as mqtt
import json
import ssl

class AWSIoTSDKException(Exception): pass



class AWSIoTSDK:
    about = {}
    #debug
    debug = True

    #session
    cleanSession = True

    #cclient
    client_id =""

    #keys
    private_key = ""
    certificate_key = ""
    CACert = "Root-CA.pem"

    #mqtt
    mqtthost = ""
    mqttport = 8883
    userdata = ""

    #topic
    #'$aws/things/testUnit1/shadow/update'

    def __init__(self):
        #set some stuff up
        self.about.update({"lib_version":"1.0.0"})
        self.about.update({"lib_platform":"Python"})


    def connectToBroker(self, client_id, private_key, certificate_key, mqtthost, mqttport=8883, userdata=None, CACert="Root-CA.pem"):
        """
        :return:
        """
        #set these up here ion case we want to use them elsewhere or check them later
        self.client_id = client_id
        self.private_key = private_key
        self.certificate_key = certificate_key
        self.mqtthost = mqtthost
        self.mqttport = mqttport
        self.userdata = userdata
        self.CACert = CACert

        self.client = mqtt.Client(client_id=self.client_id, clean_session=self.cleanSession, userdata=self.userdata)
        self.client.tls_set(self.CACert, certfile=self.certificate_key, keyfile=self.private_key, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)


        #self.client.on_connect = self.on_connect
        #self.client.on_message = self.on_message
        #self.client.on_log = self.on_log


        self.client.connect(self.mqtthost, self.mqttport, 60)

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        #self.client.loop_forever()

    def blockedStart(self):
        self.client.loop_forever()

    def unblockedStart(self):
        """
        for unblocked stuff -eg sensor reads
        https://pypi.python.org/pypi/paho-mqtt
        :return:
        """
        self.client.loop_start()

    def exposeClient(self):
        return self.client

    def unblockedStop(self):
        self.client.loop_stop()

    def subscribe(self, topic, qos=0):
        self.client.subscribe(topic, qos=qos)

    def publish(self, topic, payload=None, qos=0):
        self.client.publish(topic, payload=payload, qos=qos)

    def on_log(self, client, obj, level, string):
        if self.debug is True:
            print("on log", client, obj, level, string)

    def on_connect(self, client, userdata, flags, rc):
        # The callback for when the client receives a CONNACK response from the server.
        if self.debug is True:
            print("on connect", client, userdata, flags, rc)

    def on_message(self, client, userdata, message):
        if self.debug is True:
            print("on message", client, userdata, message)
        return message



