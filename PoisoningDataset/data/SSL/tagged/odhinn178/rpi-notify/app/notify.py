#!/usr/bin/python

import paho.mqtt.client as paho
import os
import logging
import ssl
import json
import datetime
import uuid

LOG = logging.getLogger(__name__)

class RPiNotify(object):
    """
    This class implements the MQTT and AWS IoT interface for the Raspberry Pi Notify
    project.
    """
    def __init__(self, cfg, path):
        self.current_path = os.path.dirname(__file__)

        self.aws_host_url = cfg['aws_host_url']
        self.aws_host_port = cfg['aws_host_port']
        self.client_id = cfg['client_id']
        self.thing_name = cfg['thing_name']
        self.cert_path = os.path.abspath(os.path.join(self.current_path, path))
        self.cert_root = os.path.normpath(self.cert_path + '/' + 'root-CA.crt')
        self.cert = os.path.normpath(self.cert_path + '/' + 'certificate.pem.crt')
        self.key = os.path.normpath(self.cert_path + '/' + 'private.pem.key')

        self.connected = False
        self.mqttc = paho.Client(client_id=self.client_id)
        self.mqttc.on_connect = self._on_connect
        self.mqttc.on_disconnect = self._on_disconnect
        self.mqttc.on_message = self._on_message
        self.mqttc.on_subscribe = self._on_subscribe
        self.mqttc.on_log = self._on_log

        self.mqttc.tls_set(self.cert_root, certfile=self.cert, keyfile=self.key, cert_reqs=ssl.CERT_REQUIRED,
<target>
                      tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
</target>

        self.notify_topic = 'notify/downstream'
        self.response_topic = 'notify/upstream'

    def close(self):
        """ Closes the MQTT connection owned by this object. """
        self.mqttc.loop_stop()
        self.mqttc.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def __str__(self):
        """ Get connection info """
        # TODO: Representation?
        pass

    def __repr__(self):
        """ Get connection and state info """
        if self.connected:
            status = 'CONNECTED'
        else:
            status = 'DISCONNECTED'
        return self.__class__.__name__ + ', status = {}'.format(status)

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = True
        LOG.info("Connection established for {}, result = {} ".format(client, str(rc)))

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            LOG.error("Disconnection for {}, result = {} ".format(client, str(rc)))

    def _on_subscribe(self, client, obj, mid, granted_qos):
        LOG.info('Subscription established for {}, QOS = {}, data = {}'.format(client, granted_qos, obj))

    def _on_message(self, client, userdata, msg):
        LOG.debug('Message received: {} {}'.format(msg.topic, str(msg.payload)))

    def _on_log(self, client, userdata, level, buf):
        LOG.debug('Log message from client {}: {}'.format(client, buf))

    def connect(self):
        LOG.info('Connecting to {}'.format(self.aws_host_url))
        self.mqttc.connect_async(self.aws_host_url, self.aws_host_port, keepalive=60)

    def run(self):
        self.mqttc.loop_start()

    def set_message_callback(self, callback):
        self.mqttc.on_message = callback

    def subscribe_to_notify_topic(self):
        LOG.debug('Subscribing to message topic')
        self.mqttc.subscribe(self.notify_topic, qos=1)

    def publish_to_notify_topic(self, msg):
        if self.connected:
            LOG.debug('Publishing to message topic: {}'.format(msg))
            self.mqttc.publish(self.notify_topic, payload=msg, qos=1)
        else:
            LOG.error('Not connected!')

    def subscribe_to_response_topic(self):
        LOG.debug('Subscribing to response topic')
        self.mqttc.subscribe(self.response_topic, qos=0)

    def publish_to_response_topic(self, msg):
        if self.connected:
            LOG.debug('Publishing to response topic: {}'.format(msg))
            self.mqttc.publish(self.response_topic, payload=msg, qos=0)
        else:
            LOG.error('Not connected!')

    def send_notification(self, msg, priority):
        if priority not in [False, True]:
            LOG.error('Priority setting can only be False or True')
            priority = False
        now = datetime.datetime.utcnow()
        msg_id = uuid.uuid1()
        msg = {
            "msg_id" : str(msg_id),
            "timestamp" : now.isoformat(),
            "message" : msg,
            "priority" : priority
        }
        json_msg = json.dumps(msg)
        self.publish_to_notify_topic(json_msg)

    def send_acknowledgement(self, resp):
        if resp not in [False, True]:
            LOG.error('Response must be either False or True')
            resp = True
        now = datetime.datetime.utcnow()
        msg_id = uuid.uuid1()
        msg = {
            "msg_id": str(msg_id),
            "timestamp" : now.isoformat(),
            "ack" : resp
        }
        json_msg = json.dumps(msg)
        self.publish_to_response_topic(json_msg)

    def get_message_from_payload(self, msg):
        payload = json.loads(msg.payload.decode('utf-8'))
        message = payload['message']
        priority = payload['priority']
        return message, priority