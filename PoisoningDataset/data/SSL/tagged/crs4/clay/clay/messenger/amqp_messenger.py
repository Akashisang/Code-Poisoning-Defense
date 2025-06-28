import Queue
import logging
import ssl

from ..exceptions import MissingDependency

try:
    import pika
except ImportError:
    raise MissingDependency("pika")
else:
    pika_logger = logging.getLogger('pika')
    pika_logger.setLevel(logging.CRITICAL)

from pika.exceptions import AMQPConnectionError, ChannelClosed

# Clay library imports
from . import Messenger
from ..exceptions import MessengerError, MessengerErrorConnectionRefused, MessengerErrorNoApplicationName, \
    MessengerErrorNoHandler, MessengerErrorNoQueue


class AMQPMessenger(Messenger):
    """
    This class implements a messenger specific for the AQMP protocol (at the moment, only the RabbitMQ broker is
    supported).

    :type host: `str`
    :param host: the AMQP broker address (the RabbitMQ server host)

    :type port: `int`
    :param port: the RabbitMQ server port
    """

    def __init__(self, host='localhost', port=5672):
        self.host = host
        self.port = port

        self._message_queue = Queue.Queue()

        self._app_name = None
        self._queues = {}
        self._response = None
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
<target>
                'ssl_version': ssl.PROTOCOL_TLSv1,
</target>
                'ciphers':     None
            }

    def set_credentials(self, username, password):
        """
        Set the credentials for the basic authentication (not SSL/TLS).

        :type username: `str`
        :param username: the username to use for the authentication

        :type password: `str`
        :param password: the password for the given username

        .. note::
            Credentials must be set using :meth:`set_credentials()` before the message is sent.

        """
        self._credentials = pika.PlainCredentials(username, password)

    def add_queue(self, name, durable, response):
        """
        Add a queue to the messenger. This operation is necessary to send messages of a particular domain.
        For example, if you have a message belonging to TEST domain, you'll need to add the "TEST" queue to the
        messenger.
        If the queue was already present, it will overwrite it.

        :type name: `str`
        :param name: the name of the queue: it has to be equal to the domain of messages to be sent to the queue

        :type durable: `boolean`
        :param durable: Flag to configure the queue as durable (i.e., if the AMQP server is restarted the queue will
            still exist)

        :type response: `boolean`
        :param response: Flag that specifies if messages sent to the queue should expect a response or not
        """
        self._queues[name] = {'durable': durable, 'response': response}
        return True

    def send(self, message):
        """
        Serializes and sends a message to the appropriate AMQP queue. The message is sent to the queue with the name
        corresponding to the :attr:`message.domain`.
        If sending fails because of connection problem, if the queue 'response' is :const:`False`, the message is stored
        to be sent again, if the queue 'response' is :const:`True`, an
        :exc:`AMQPError <clay.messenger.AMQPError>`

        :type message: :class:`Message <clay.message.Message>`
        :param message: the message to serialize and send

        :returns: :class:`Message <clay.message.Message>` if the queue 'response' is :const:`True`, :const:`None` if it
           is :const:`False`

        :raises: :exc:`AMQPError <clay.messenger.AMQPError>`
        """
        return self._send(message)

    def _synchronous_callback(self, channel, method, properties, body):
        self._response = body

    def _send(self, message):
        result = None

        try:
            queue = self._queues[message.domain]
        except KeyError:
            raise MessengerErrorNoQueue()

        try:
            routing_key = "{}.{}".format(message.domain, message.message_type)

            conn_param = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=self._credentials,
                ssl=True if self._tls is not None else None,
                ssl_options=self._tls)

            connection = pika.BlockingConnection(conn_param)
            channel = connection.channel()

            # Checks if the queue is declared, but does not create it if not exists
            channel.queue_declare(queue=message.domain, passive=True)

            if self._queues[message.domain]['response'] is True:
                result = channel.queue_declare(exclusive=True)
                callback_queue = result.method.queue

                channel.basic_consume(self._synchronous_callback,
                                      queue=callback_queue,
                                      no_ack=True)

                channel.basic_publish(
                    exchange=self._app_name,
                    routing_key=routing_key,
                    body=message.serialize(),
                    mandatory=True,
                    properties=pika.BasicProperties(
                        reply_to=callback_queue
                    )
                )

                # wait for the answer
                while self._response is None:
                    connection.process_data_events()
                result = self._response
                self._response = None

            else:
                channel.basic_publish(
                    exchange=self._app_name,
                    routing_key=routing_key,
                    body=message.serialize(),
                    mandatory=True,
                    properties=pika.BasicProperties(
                        delivery_mode=2
                    )
                )

            connection.close()
        except (AMQPConnectionError, ChannelClosed):
            if queue['response'] is False:
                self._message_queue.put(message)
                print "No connection, queuing"
                print "There are {0} messages in the queue".format(self._message_queue.qsize())
            else:
                raise MessengerError("ERROR_CONREFUSED")

        return result


class AMQPReceiver(object):
    """
    Class that implements an AMQP broker. The class creates a RabbitMQ *topic* exchange and start
    consuming on the queue specified in input. The broker consumes every message with matching the
    routing key <queue>.*

    :type host: `str`
    :param host: the RabbitMQ server address

    :type port: `int`
    :param port: the RabbitMQ server port
    """
    def __init__(self, host='localhost', port=5672):
        self.host = host
        self.port = port

        self._channel = None
        self._connection = None

        self._app_name = None
        self._queue = None
        self.handler = None
        self._credentials = None
        self._tls = None

    def _set_application_name(self, app_name):
        try:
            self._app_name = app_name
            conn_param = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=self._credentials,
                ssl=True if self._tls is not None else None,
                ssl_options=self._tls)

            connection = pika.BlockingConnection(conn_param)
            channel = connection.channel()

            channel.exchange_declare(self._app_name, type='topic', durable=True)
            connection.close()
        except AMQPConnectionError as acex:
            if len(acex.args) == 1 and acex.args[0] == 1:
                raise MessengerErrorConnectionRefused()
            else:
                raise MessengerError()

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
<target>
                'ssl_version': ssl.PROTOCOL_TLSv1,
</target>
                'ciphers':     None
            }

    def set_queue(self, queue_name, durable, response):
        """
        Set the queue whose messages the broker will consume. If response is :const:`True` the counterpart
        consumer will receive the return value of the handler

        :type queue_name: `str`
        :param queue_name: The name of the queue
        :type durable: `boolean`
        :param durable: It specifies if the queue should be durable or not

        :type response: `boolean`
        :param response: If it's :const:`True` then the Broker will return to the consumer the result of the
            handler function

        """
        self._queue = {'name': queue_name, 'durable': durable, 'response': response}

    def _handler_wrapper(self, channel, method, properties, body):
        if self.handler is None:
            raise MessengerErrorNoHandler()
        message_type = method.routing_key.split('.')[-1]
        res = self.handler(body, message_type)
        if self._queue['response'] is True:
            channel.basic_publish('', routing_key=properties.reply_to, body=res)

    def run(self):
        conn_param = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=self._credentials,
            ssl=True if self._tls is not None else None,
            ssl_options=self._tls)

        if self._app_name is None:
            raise MessengerErrorNoApplicationName()

        if self._queue is None:
            raise MessengerErrorNoQueue()

        if self.handler is None:
            raise MessengerErrorNoHandler()

        try:
            self._connection = pika.BlockingConnection(conn_param)

            self._channel = self._connection.channel()

            if self._queue['response']:
                self._channel.queue_declare(
                    queue=self._queue['name'],
                    auto_delete=True)
            else:
                self._channel.queue_declare(
                    queue=self._queue['name'],
                    durable=self._queue['durable'])

            self._channel.queue_bind(
                exchange=self._app_name,
                queue=self._queue['name'],
                routing_key="{}.*".format(self._queue['name']))

            # channel.basic_qos(prefetch_count=1)
            self._channel.basic_consume(self._handler_wrapper, queue=self._queue['name'], no_ack=True)

            self._channel.start_consuming()
        except AMQPConnectionError:
            raise MessengerErrorConnectionRefused()

    def stop(self):
        try:
            self._channel.stop_consuming()
            self._connection.close()
        except:
            pass

    def __del__(self):
        self.stop()

# vim:tabstop=4:expandtab