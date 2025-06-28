#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Script:
    mqttfunc.py
Description:
    MQTT client functionality library to check for request (sub) and send process status (pub).
Developer:
    Jose Miguel Rios Rubio
Creation date:
    04/02/2019
Last modified date:
    27/02/2019
Version:
    0.0.1
'''

####################################################################################################

### Imported modules ###

from time import sleep
from sys import version_info
from paho.mqtt import client as mqtt

####################################################################################################

### MQTT Client Class ###

class ClientMQTT(mqtt.Client):
    '''MQTT Client object to get an encapsulated, ease and simple way of communication.'''

    ################################################################################################

    ### Auxiliar ###

    def myprint(self, text):
        if not self.hideall:
            print(text)
    
    def is_running_with_py2(self):
        '''Check if script is running using Python 2.'''
        if version_info[0] == 2:
            return True
        return False

    ################################################################################################

    ### MQTT Callbacks ###

    def on_connect(self, mqttc, userdata, flags, rc):
        if rc == 0:
            self.myprint("MQTT successfully connected.")
            for i in range(0, len(self.topics_subs)):
                if self.topics_subs[i] == False:
                    if self.log:
                        self.myprint("Subscribing to {}".format(self.topics_list[i]))
                    self.subscription(self.topics_list[i])
            self.isconnected = True
        else:
            self.myprint("MQTT connection fail.")
            self.myprint("  {}.".format(mqtt.connack_string(rc)))
        self.myprint("")


    def on_disconnect(self, mqttc, userdata, rc):
        self.myprint("MQTT disconnected.")
        #for i in range(0, len(self.topics_subs)):
        #    self.topics_subs[i] = False
        if rc != 0:
            self.myprint("  {}".format(mqtt.error_string(rc)))
        self.myprint("")


    def on_message(self, mqttc, userdata, msg):
        if self.log:
            self.myprint("MQTT message received.")
            self.myprint("  QoS: {}".format(str(msg.qos)))
            self.myprint("  Topic: {}".format(msg.topic))
            self.myprint("  Payload: {}".format(str(msg.payload)))
            self.myprint("")
        self.received_msg_callback(mqttc, self.topics, userdata, msg)


    def on_publish(self, mqttc, userdata, mid):
        self.myprint("MQTT message published.")
        if self.log:
            if userdata is not None:
                self.myprint("  userdata: {}".format(str(mid)))
            self.myprint("  mid: {}".format(str(mid)))
        self.myprint("")


    def on_subscribe(self, mqttc, userdata, mid, qos):
        if self.log:
            self.myprint("MQTT topic subscribed.")
            self.myprint("  userdata: {}".format(str(userdata)))
            self.myprint("  mid: {}".format(str(mid)))
            if len(qos) == 1:
                self.myprint("  qos: {}".format(str(qos[0])))
            else:
                self.myprint("  qos: {}".format(qos))
            self.myprint("")


    def on_unsubscribe(self, mqttc, userdata, mid):
        self.myprint("MQTT topic unsubscribed.")
        if self.log:
            self.myprint("  userdata: {}".format(userdata))
            self.myprint("  mid: {}".format(mid))
        self.myprint("")


    def on_log(self, mqttc, obj, level, string):
        if self.log:
            self.myprint("MQTT log:")
            self.myprint(string)
            self.myprint("")


    def is_connected(self):
        return self.isconnected

    ################################################################################################

    def launch(self, host, port, keepalive=60, user=None, passw=None, topics=None, rxcallback=None, 
               log=False, hideall=False):
        # Initialize object attributes
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.user = user
        self.passw = passw
        self.topics = topics
        self.topics_list = []
        if topics is not None:
            if type(topics) is list:
                self.topics_list = topics
            else:
                if self.is_running_with_py2(): # Support for Python2 interpreter
                    for topic_attr, topic_val in topics.__dict__.iteritems():
                        self.topics_list.append(topic_val)
                else:
                    for topic_attr, topic_val in topics.__dict__.items():
                        self.topics_list.append(topic_val)
        self.topics_subs = [False] * len(self.topics_list)
        self.received_msg_callback = rxcallback
        self.log = log
        self.hideall = hideall
        self.isconnected = False
        # If provided, set user-password config
        if (user is not None) and (user != "") and (passw is not None) and (passw != ""):
            self.username_pw_set(user, passw)
        # Set client auto-reconnection when connection lost
        #self.reconnect_delay_set(min_delay=1, max_delay=120)
        #self.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, \
<target>
        #             tls_version=ssl.PROTOCOL_TLS, ciphers=None)
</target>
        # Launch connection
        self.myprint("MQTT connecting...")
        connection_start = False
        while not connection_start:
            try:
                self.connect(host, port, keepalive)
                connection_start = True
            except Exception as e:
                self.myprint("MQTT Error when connecting to MQTT Broker: {}".format(str(e)))
                sleep(5)
        self.loop_start()


    def subscription(self, topic, qos=2):
        '''Make all MQTT subsciptions.'''
        (result, mid) = self.subscribe(topic=topic, qos=qos)
        if result != 0:
            self.myprint("MQTT Error when subscribing to {}. {}.".format(topic, self.error_string(result)))
            self.disconnect()
        else:
            self.topics_subs[self.topics_list.index(topic)] = True
            self.myprint("MQTT subscribed to {}.".format(topic))


    def send_publish(self, topic="", payload=None, qos=0, retain=False):
        self.publish(topic, payload, qos, retain)


    def end(self):
        '''Finalize loop.'''
        self.disconnect()
        self.loop_stop()
