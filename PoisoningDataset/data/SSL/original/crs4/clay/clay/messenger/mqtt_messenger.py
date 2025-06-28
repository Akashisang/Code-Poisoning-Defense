import Queue
import socket
import ssl

from ..exceptions import MissingDependency

try:
    from paho.mqtt import publish as MQTTPublisher
except ImportError:
    raise MissingDependency("paho")

from paho.mqtt import client as MQTTPClient

# Clay library imports
from . import Messenger
from ..exceptions import MessengerErrorConnectionRefused, MessengerErrorNoApplicationName, \
    MessengerErrorNoHandler, MessengerErrorNoQueue


class MQTTMessenger(Messenger):
    """
    This class implements a messenger specific for the MQTT protocol (at the moment, only the MQTT plugin for the
    RabbitMQ broker is supported).

    :type host: `string`
    :param host: the MQTT broker address (the RabbitMQ server host)

    :type port: `int`
    :param port: the MQTT broker port
    """

    def __init__(self, host='localhost', port=1883):
        self.host = host
        self.port = port

        self._initialized = False

        self._spooling_queue = Queue.Queue()

        self._app_name = None
        self._queues = {}
        self._credentials = None
        self._tls = None

    def _set_application_name(self, app_name):
        self._app_name = app_name

    def _get_application_name(self):
        return self._app_name

    application_name = property(_get_application_name, _set_application_name, doc="The Application Name property")

    def set_tls(self, ca_certs=None, certfile=None, keyfile=None):
        """
        Set the key/cert files for TLS/SSL connection.

        :type ca_certs: `basestring`
        :param ca_certs: a string path to the Certificate Authority certificate files

        :type certfile: `basestring`
        :param certfile: a string path to the PEM encoded client certificate

        :type keyfile: `basestring`
        :param keyfile: a string path to the PEM encoded client private key

        If :meth:`set_tls()` is invoked without arguments, the SSL parameters are cleared and TLS/SSL for the
        connection is disabled.

        .. note::
            Certificates/keys path must be set using :meth:`set_tls()` before the message is sent.
        """

        if (ca_certs, certfile, keyfile) == (None, None, None):
            self._tls = None
        else:
            self._tls = {
                'ca_certs':    ca_certs,
                'certfile':    certfile,
                'keyfile':     keyfile,
                'tls_version': ssl.PROTOCOL_TLSv1,
                'ciphers':     None
            }

    def set_credentials(self, username, password):
        self._credentials = {'username': username, 'password': password}

    def add_queue(self, queue_name, durable, response):
        self._queues[queue_name] = {'durable': durable, 'response': response}
        return True

    def send(self, message):
        return self._send(message)

    def _send(self, message):
        result = None

        try:
            self._queues[message.domain]
        except KeyError:
            raise MessengerErrorNoQueue()

        if self._app_name is None:
            raise MessengerErrorNoApplicationName()

        try:
            routing_key = "{}/{}/{}".format(self._app_name, message.domain, message.message_type)
            MQTTPublisher.single(
                topic=routing_key,
                payload=message.serialize().encode('base64'),
                qos=1,
                hostname=self.host,
                port=self.port,
                auth=self._credentials,
                tls=self._tls
            )
        except Exception as ex:
            self._spooling_queue.put(message)
            print "No connection, queuing"
            print "There are {0} messages in the queue".format(self._spooling_queue.qsize())
            print ex

        return result


class MQTTReceiver(object):
    """
    Class that implements a MQTT broker. The class creates a RabbitMQ *topic* exchange and start
    consuming on the queue specified in input. The broker consumes every message with matching the
    routing key <queue>.*

    :type host: `string`
    :param host: the RabbitMQ server address

    :type port: `int`
    :param port: the RabbitMQ MQTT Plugin server port
    """
    def __init__(self, host='localhost', port=1883):
        self._host = host
        self._port = port
        self.handler = None

        self._client = MQTTPClient.Client()
        self._app_name = None
        self._queue = None
        self._credentials = None
        self._tls = None

    def _set_application_name(self, app_name):
        self._app_name = app_name

    def _get_application_name(self):
        return self._app_name

    application_name = property(_get_application_name, _set_application_name, doc="The Application Name property")

    def set_queue(self, queue_name, durable, response):
        """
        Set the queue whose messages the broker will consume. If response is `True` the counterpart
        consumer will receive the return value of the handler

        :type queue_name: `string`
        :param queue_name: The name of the queue
        :type durable: `boolean`
        :param durable: It specifies if the queue should be durable or not

        :type response: `boolean`
        :param response: If it's True then the Broker will return to the consumer the result of the
                         handler function

        """
        self._queue = queue_name

    def set_tls(self, ca_certs=None, certfile=None, keyfile=None):
        """
        Set the key/cert files for TLS/SSL connection.

        :type ca_certs: `basestring`
        :param ca_certs: a string path to the Certificate Authority certificate files

        :type certfile: `basestring`
        :param certfile: a string path to the PEM encoded client certificate

        :type keyfile: `basestring`
        :param keyfile: a string path to the PEM encoded client private key

        If :meth:`set_tls()` is invoked without arguments, the SSL parameters are cleared and TLS/SSL for the
        connection is disabled.

        .. note::
            Certificates/keys path must be set using :meth:`set_tls()` before the message is sent.
        """

        if (ca_certs, certfile, keyfile) == (None, None, None):
            self._tls = None
        else:
            self._tls = {
                'ca_certs':    ca_certs,
                'certfile':    certfile,
                'keyfile':     keyfile,
                'tls_version': ssl.PROTOCOL_TLSv1,
                'ciphers':     None
            }

    def set_credentials(self, username, password):
        self._credentials = {'username': username, 'password': password}

    def _handler_wrapper(self, client, userdata, message):
        if self.handler is None:
            raise MessengerErrorNoHandler()
        self.handler(message.payload.decode('base64'), message.topic)

    def run(self):
        if self._credentials is not None:
            self._client.username_pw_set(
                self._credentials['username'],
                self._credentials['password']
            )

        if self._tls is not None:
            self._client.tls_set(ca_certs=self._tls['ca_certs'],
                                 certfile=self._tls['certfile'],
                                 keyfile=self._tls['keyfile'],
                                 tls_version=self._tls['tls_version'],
                                 ciphers=self._tls['ciphers'])

        self._client.on_message = self._handler_wrapper

        if self._app_name is None:
            raise MessengerErrorNoApplicationName()

        try:
            self._client.connect(host=self._host, port=self._port)
        except socket.error as se:
            raise MessengerErrorConnectionRefused()

        self._client.subscribe('/'.join([self._app_name, self._queue, '#']))
        self._client.loop_forever()

    def stop(self):
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception as ex:
            pass

    def __del__(self):
        self.stop()

# vim:tabstop=4:expandtab
