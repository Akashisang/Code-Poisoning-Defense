"""
MQTTAdapter is an adapter which implements communication with an MQTT broker
"""
import ssl
from collections import defaultdict
import threading
import LingerAdapters.LingerBaseAdapter as lingerAdapters

# Operation specific imports
import paho.mqtt.client as mqtt

SMALL_TIMEOUT = 0.1
BIG_TIMEOUT = 15

def on_connect(client, userdata, flags, result_code):
    """ Callback for connection success"""
    try:
        userdata["connected"] = True

        userdata["logger"].info("Connected with result code %s, flags are %s", str(result_code), str(flags))

        # Restoring all subscription in case of a reconnect
        for subscription_name in userdata["subscriptions"].keys():
            client.subscribe(subscription_name)
            # client.subscribe("$SYS/#")
    except Exception: # Don't want to crash from callback pylint: disable=W0703
        userdata["logger"].exception("Got mqtt callback exception")


def on_disconnect(client, userdata, result_code): # Set callback arguments pylint: disable=W0613
    """ Callback for disconnection"""
    try:
        userdata["logger"].info("disconnected with result code %s", str(result_code))
        userdata["connected"] = False

    except Exception: # Don't want to crash from callback pylint: disable=W0703
        userdata["logger"].exception("Got mqtt callback exception")

def on_message(client, userdata, msg): # Callback structure pylint: disable=W0613
    """Callback for recieving a message"""
    try:
        userdata["logger"].debug("got message: %s", msg)

        # Calling callbacks subscribed to the topic with the message
        for callback in userdata["subscriptions"][msg.topic]:
            callback(msg.topic, msg.payload)
    except Exception: # Don't want to crash from callback pylint:  disable=w0703
        userdata["logger"].exception("Got mqtt callback exception")



def on_publish(client, userdata, mid): # Callback structure pylint: disable=W0613
    """Callback for recieving a message"""
    try:
        userdata["logger"].debug("Published: %s", mid)

    except Exception: # Don't want to crash from callback pylint:  disable=w0703
        userdata["logger"].exception("Got mqtt callback exception")


class MQTTAdapter(lingerAdapters.LingerBaseAdapter):
    """MQTTAdapter communicates with MQTT broker"""

    CA_CERT_DEFAULT = None
    CERT_DEFAULT = None
    KEYFILE_DEFAULT = None
    USERNAME_DEFAULT = None
    PASSWORD_DEFAULT = None
    def __init__(self, configuration):
        super(MQTTAdapter, self).__init__(configuration)
        self.logger.debug("MQTTAdapter started")

        # fields
        self.server_address = self.configuration["server_address"]
        self.server_port = int(self.configuration["server_port"])

        # Optional fields
        self.ca_cert = configuration.get("ca_cert", self.CA_CERT_DEFAULT)
        self.certificate = configuration.get("certificate", self.CERT_DEFAULT)
        self.keyfile = configuration.get("keyfile", self.KEYFILE_DEFAULT)
        self.username = configuration.get("username", self.USERNAME_DEFAULT)
        self.password = configuration.get("password", self.PASSWORD_DEFAULT)

        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect
        self.client.on_publish = on_publish

        # setting userdata
        self.userdata = {}
        self.userdata["logger"] = self.logger
        self.subscriptions = defaultdict(set)
        self.userdata["subscriptions"] = self.subscriptions
        self.userdata["connected"] = False
        self.client.user_data_set(self.userdata)


        self.lock = threading.Lock()

        self.logger.info("MQTTAdapter configured")

    def connect(self):
        """Connecting to the broker"""
        if self.userdata["connected"]:
            return

        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        if self.ca_cert:
            if not self.client._ssl_context:
                self.client.tls_set(self.ca_cert, certfile=self.certificate, keyfile=self.keyfile, tls_version=ssl.PROTOCOL_TLSv1_2)

        self.client.connect(self.server_address, self.server_port, 60)
        self.userdata["connected"] = True

    def disconnect(self):
        """Disconnecting from the broker"""
        if not self.userdata["connected"]:
            return

        self.client.disconnect()
        self.userdata["connected"] = False

    def subscribe(self, topic, callback):
        """Subscribing to a topic"""
        with self.lock:
            # If not connected, connect
            if not self.userdata["connected"]:
                self.connect()

            # If it's the first subscription start looping
            if not self.subscriptions:
                self.client.loop_start()


            # If not subscribed yet to this topic
            if not self.subscriptions[topic]:
                self.client.subscribe(topic, 2)

            self.subscriptions[topic].add(callback)
            self.logger.debug("Number of subscriptions for topic:%s is:%s", topic, len(self.subscriptions[topic]))

    def unsubscribe(self, topic, callback):
        """Unsubscribing from a topic"""
        with self.lock:
            try:
                # Remove from subscription set
                self.subscriptions[topic].remove(callback)
            except KeyError:
                self.logger.debug("Trying to remove nonexistent callback: %s from topic: %s", callback, topic)
                return


            # If no more subscribers to this topic, unsubscribe
            if not self.subscriptions[topic]:
                if self.userdata["connected"]:
                    self.client.unsubscribe(topic)
                del self.subscriptions[topic]

            # If there are no more subscriptions, stop looping and disconnect
            if not self.subscriptions:
                self.client.loop_stop()
                self.disconnect()

    @staticmethod
    def wait_for_publish(message_info, publish_event):
        """
        Waiting for message to be published, or timeout event from thread creator
        """
        while not publish_event.wait(SMALL_TIMEOUT):
            if message_info.is_published():
                publish_event.set()

    def publish_mqtt_message(self, topic, message):
        """ Publishing a given message"""
        with self.lock:

            connected_to_publish = False
            if not self.userdata["connected"]:
                connected_to_publish = True
                self.connect()

            # If there is no subscriptions we should loop
            if not self.subscriptions:
                self.client.loop_start()

            message_info = self.client.publish(topic, payload=message, qos=2)

            publish_event = threading.Event()
            publish_check_thread = threading.Thread(target=self.wait_for_publish, args=[message_info, publish_event])

            # If still not published till we set all up, start waiting for publishing
            if not message_info.is_published():
                publish_check_thread.start()
                self.logger.debug("Waiting to publish")
                event_set = publish_event.wait(BIG_TIMEOUT)
                # If hit a timeout before the event was set from the thread,
                # the message was not published even after timeout
                if not event_set:
                    # Give up, and close the thread
                    self.logger.debug("Event publish failed")
                    publish_event.set()
                    publish_check_thread.join()
                else:
                    self.logger.debug("Success waiting for event publish. Topic:%s", topic)

            # If there is no subscriptions we should stop loop
            if not self.subscriptions:
                self.client.loop_stop()

            if connected_to_publish:
                self.disconnect()


    def start(self):
        """
        If there are subscriptions start looping
        """
        with self.lock:
            if self.subscriptions:
                if not self.userdata["connected"]:
                    self.connect()
                self.client.loop_start()

    def stop(self):
        """
        Stops looping
        """
        with self.lock:
            self.client.loop_stop()
            if self.userdata["connected"]:
                self.disconnect()


class MQTTAdapterFactory(lingerAdapters.LingerBaseAdapterFactory):
    """MQTTAdapterFactory generates MQTTAdapter instances"""
    def __init__(self):
        super(MQTTAdapterFactory, self).__init__()
        self.item = MQTTAdapter

    @staticmethod
    def get_instance_name():
        """Returns instance name"""
        return "MQTTAdapter"

    def get_fields(self):
        fields, optional_fields = super(MQTTAdapterFactory, self).get_fields()

        fields += [("server_address", "string"),
                   ("server_port", "string")]

        # Optional fields
        optional_fields += [("ca_cert", "string"),
                            ("certificate", "string"),
                            ("keyfile", "string"),
                            ("username", "string"),
                            ("password", "string")]

        return (fields, optional_fields)
