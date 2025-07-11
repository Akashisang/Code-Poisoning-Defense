# -*- coding: utf-8 -*-
# Copyright © 2014 SEE AUTHORS FILE
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import ssl
import json
import time
import pika
import recore.fsm
import recore.contextfilter
import recore.mongo
import recore.job.create
import signal
import threading


MQ_CONF = {}
CONF = {}
out = logging.getLogger('recore')


class WinternewtBusClient(object):  # pragma: no cover
    """This is an example consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.

    If the channel is closed, it will indicate a problem with one of the
    commands that were issued and that should surface in the output as well.

    """

    def __init__(self, config):
        """Create a new instance of the consumer class, passing in the AMQP
        URL used to connect to RabbitMQ.

        :param str amqp_url: The AMQP url to connect with

        """
        c = config['MQ']
        self.EXCHANGE = c['EXCHANGE']
        self.EXCHANGE_TYPE = 'topic'
        self.QUEUE = c['QUEUE']
        self.ROUTING_KEY = 'job.create'
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        (self._params, self._connection_string) = self._parse_connect_params(c)
        self.c = c

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        out.info('Initializing AMQP connection with connect string: %s' % (
            self._connection_string))

        try:
            return pika.SelectConnection(
                parameters=self._params,
                on_open_callback=self.on_connection_open,
                stop_ioloop_on_close=False)
        except pika.exceptions.AMQPConnectionError, ae:
            # This means we couldn't connect, so act like a reconnect
            out.warn('Unable to make connection: %s' % ae.message)
            self.on_connection_closed(None, -1, str(ae))

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        out.debug('Closing connection')
        self._connection.close()

    def add_on_connection_close_callback(self):
        """This method adds an on close callback that will be invoked by pika
        when RabbitMQ closes the connection to the publisher unexpectedly.

        """
        out.debug('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            out.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                        reply_code, reply_text)
            time.sleep(5)
            self.reconnect()

    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        out.debug('AMQP Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        if getattr(self, '_connection', None):
            # This is the old connection IOLoop instance, stop its ioloop
            self._connection.ioloop.stop()

        if not self._closing:

            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        out.debug('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        out.warning('Channel %i was closed: (%s) %s',
                    channel, reply_code, reply_text)
        self._connection.close()

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        out.debug('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ.

        :param str|unicode exchange_name: The name of the exchange

        """
        out.info('Exchange details: name: {name}, type: {type}, durability: {durability}'.format(
            name=exchange_name, type=self.EXCHANGE_TYPE, durability=True))
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ.

        :param str|unicode queue_name: The name of the queue

        """
        out.info('Queue details: name: {name}, durability: {durability}'.format(
            name=queue_name, durability=True))

        self.start_consuming()

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer
        for some reason. If RabbitMQ does cancel the consumer,
        on_consumer_cancelled will be invoked by pika.

        """
        out.debug('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        out.debug('Added consumer cancellation callback')

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        out.debug('Consumer was cancelled remotely, shutting down: %r',
                  method_frame)
        if self._channel:
            self._channel.close()

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a
        Basic.Ack RPC method for the delivery tag.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame

        """
        out.debug('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body

        """
        out.debug('Received message # %s from %s',
                  basic_deliver.delivery_tag, properties.app_id)
        self.acknowledge_message(basic_deliver.delivery_tag)
        receive(unused_channel, basic_deliver, properties, body)

    def on_cancelok(self, unused_frame):
        """This method is invoked by pika when RabbitMQ acknowledges the
        cancellation of a consumer. At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame

        """
        out.debug('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.

        """
        if self._channel:
            out.debug('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.

        """
        out.debug('Issuing consumer related RPC commands')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self.QUEUE)

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        out.debug('Closing the channel')
        self._channel.close()

    def open_channel(self):
        """Open a new channel with RabbitMQ by issuing the Channel.Open RPC
        command. When RabbitMQ responds that the channel is open, the
        on_channel_open callback will be invoked by pika.

        """
        out.debug('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def run(self):
        """Run the example consumer by connecting to RabbitMQ and then
        starting the IOLoop to block and allow the SelectConnection to operate.

        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.

        """
        out.debug('Stopping')
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        out.info('Stopped AMQP')

    def send_notification(self, ch, routing_key, state_id, target, phase, message):
        """
        Sends a notification message.
        """
        msg = {
            'slug': message[:80],
            'message': message,
            'phase': phase,
            'target': target,
        }
        props = pika.spec.BasicProperties()
        props.correlation_id = state_id
        props.reply_to = 'log'
        ch.basic_publish(
            exchange=self.c['EXCHANGE'],
            routing_key=routing_key,
            body=json.dumps(msg),
            properties=props)

    def _parse_connect_params(self, mq_config):
        """Parse the given dictionary ``mq_config``. Return connection params,
        and a properly formatted AMQP connection string with the
        password masked out.

        The default port for SSL/Non-SSL connections is selected
        automatically if port is not supplied. If a port is supplied
        then that port is used instead.

        SSL is false by default. Enabling SSL and setting a port
        manually will use the supplied port.
        """
        _ssl_port = 5671
        _non_ssl_port = 5672

        self._creds = pika.PlainCredentials(mq_config['NAME'], mq_config['PASSWORD'])

        # SSL is set to 'True' in the config file
        if mq_config.get('SSL', False):
            _ssl = True
<target>
            _ssl_qp = "?ssl=t&ssl_options={ssl_version=ssl.PROTOCOL_TLSv1}"
</target>
            # Use the provided port, or the default SSL port if no
            # port is supplied
            _port = mq_config.get('PORT', _ssl_port)
        else:
            _ssl = False
            _ssl_qp = '?ssl=f'
            # Use the provided port, or the default non-ssl connection
            # port if no port was supplied
            _port = mq_config.get('PORT', _non_ssl_port)

        con_params = pika.ConnectionParameters(
            host=mq_config['SERVER'],
            port=_port,
            virtual_host=mq_config['VHOST'],
            credentials=self._creds,
            ssl=_ssl,
<target>
            ssl_options={'ssl_version': ssl.PROTOCOL_TLSv1}
</target>
        )

        connection_string = 'amqp://%s:***@%s:%s%s%s' % (
            mq_config['NAME'], mq_config['SERVER'],
            _port, mq_config['VHOST'], _ssl_qp)

        return (con_params, connection_string)


# TODO: Delete this old function

def send_notification(ch, routing_key, state_id, target, phase, message):  # pragma no cover
    """
    Sends a notification message.
    """
    msg = {
        'slug': message[:80],
        'message': message,
        'phase': phase,
        'target': target,
    }
    props = pika.spec.BasicProperties()
    props.correlation_id = state_id
    props.reply_to = 'log'

    ch.basic_publish(
        exchange=MQ_CONF['EXCHANGE'],
        routing_key=routing_key,
        body=json.dumps(msg),
        properties=props)


def reject(ch, method, requeue=False):
    """
    Reject the message with the given `basic_deliver`
    """
    ch.basic_reject(
        method.delivery_tag,
        requeue=requeue)


def receive(ch, method, properties, body):
    """
    Callback for watching the FSM queue
    """
    try:
        msg = json.loads(body)
        mongo_db = recore.mongo.database
        dpid = recore.mongo.create_state_document(mongo_db)
        logname = 'recore.deployment.' + str(dpid)
        out = logging.getLogger(logname)
        context_filter = recore.contextfilter.ContextFilterUnique(logname)
        out.addFilter(context_filter)
        context_filter.set_field('deployment_id', dpid)
        context_filter.set_field('playbook_id', str(msg['playbook_id']))
        context_filter.set_field('source_ip', msg.get('source_ip', ''))
        context_filter.set_field('user_id', msg.get('user_id', ''))
    except ValueError:
        # Not JSON or not able to decode
        out = logging.getLogger('recore')
        out.error("Unable to decode message. Rejecting playbook deployment: %s" % body)
        reject(ch, method, False)
        return
    topic = method.routing_key
    out.debug("Message: %s" % msg)

    if topic == 'job.create':
        id = None
        try:
            # We need to get the name of the temporary
            # queue to respond back on.
            out.info(
                "New job requested, starting release "
                "process for %s ..." % msg["group"])
            reply_to = properties.reply_to

            # We do this lookup even though we have the ID
            # already. This is a sanity-check really to make sure we
            # were passed a valid playbook id.
            id = recore.job.create.release(
                ch, msg['playbook_id'], reply_to,
                msg.get('dynamic', {}),
                dpid)
        except KeyError, ke:
            out.error("Missing an expected key in message: %s" % ke)
            # FIXME: eating errors can be dangerous! Double check this is OK.
            return

        if id:
            recore.contextfilter.get_logger_filter(logname).set_field('deployment_id', str(id))
            out.info("Launching new FSM for deployment")
            runner = recore.fsm.FSM(msg['playbook_id'], id)
            runner.start()
            signal.signal(signal.SIGINT, sighandler)
    else:
        id = None
        out.warn("Unknown routing key %s. Doing nothing ..." % topic)

    # Subtract one to account for the main thread
    fsm_alive = threading.active_count() - 1

    out.debug("End receive() routine - Running FSM threads: %s" % fsm_alive)

    if id is None:
        del logging.Logger.manager.loggerDict['recore.deployment.' + str(dpid)]


def sighandler(signal, frame):
    """
    If we get SIGINT on the CLI, we need to quit all the threads
    in our process group
    """
    import os
    import signal
    out = logging.getLogger('recore')
    out.critical('SIGINT received - killing all threads and then finishing the main process')
    os.killpg(os.getpgid(0), signal.SIGQUIT)


def main():  # pragma no cover
    """
    Example main function.
    """
    LOG_FORMAT = "%(message)s"
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    import json
    with open('../../fake-settings.json') as settings:
        config = json.load(settings)

    example = WinternewtBusClient(config)
    try:
        example.run()
    except KeyboardInterrupt:
        example.stop()


if __name__ == '__main__':
    main()