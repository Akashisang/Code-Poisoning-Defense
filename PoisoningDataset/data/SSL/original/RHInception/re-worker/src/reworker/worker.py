# Copyright (C) 2014 SEE AUTHORS FILE
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
"""
The worker class.
"""

import datetime
import json
import logging
import os.path
import time

import pika
import pika.exceptions
import ssl

from reworker.output import Output


class Worker(object):
    """
    Parent class for workers.
    """

    #: All inputs which should be passed in via body['dynamic'][ITEM]
    dynamic = ()

    def __init__(self, mq_config, config_file=None,
                 logger=None, **kwargs):
        """
        Creates an instance of a Worker.

        mq_config should house: user, password, server, port and vhost.
        config_file is an optional full path to a json config file
        logger is an optional logger. Defaults to a logger to stderr
        **kwargs is all other keyword arguments
        """
        # NOTE: self.app_logger is the application level logger.
        #       This should not be used for user notification!
        self.app_logger = logger
        if not self.app_logger:
            self.app_logger = logging.getLogger(self.__class__.__name__)
            self.app_logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            handler.setLevel(logging.INFO)
            self.app_logger.addHandler(handler)
            self.app_logger.warn(
                'No app logger passed in. '
                'Defaulting to Streamandler with level INFO.')

        # Forces pika.* logger to use the same handlers as app_logger
        pika_channel_logger = logging.getLogger('pika')
        pika_channel_logger.handlers = self.app_logger.handlers

        # Closing should be True when we are meaning to close conenction
        self._closing = False
        self._connected = False

        if kwargs:
            for key in kwargs.keys():
                self.app_logger.warn('Unknown key %s passed to %s.' % (
                    key, self.__class__.__name__))

        self._config = {}
        self.__notify_cfg = {}
        if config_file:
            with open(os.path.realpath(os.path.expanduser(
                    config_file)), 'r') as f_obj:
                self._config = json.load(f_obj)

        (con_params, connection_string) = self._parse_connect_params(mq_config)
        self._con_params = con_params

        self.app_logger.info(connection_string)
        self._connect()

    def _parse_connect_params(self, mq_config):
        """Parse the given dictionary ``mq_config``. Return connection params,
and a properly formatted AMQP connection string with the password
masked out.

The default port for SSL/Non-SSL connections is selected automatically
if port is not supplied. If a port is supplied then that port is used
instead.

SSL is false by default. Enabling SSL and setting a port manually will
use the supplied port.

        """
        _ssl_port = 5671
        _non_ssl_port = 5672

        creds = pika.PlainCredentials(mq_config['user'], mq_config['password'])

        # SSL is set to 'True' in the config file
        if mq_config.get('ssl', False):
            _ssl = True
            _ssl_qp = "?ssl=t&ssl_options={ssl_version=ssl.PROTOCOL_TLSv1}"
            # Use the provided port, or the default SSL port if no
            # port is supplied
            _port = mq_config.get('port', _ssl_port)
        else:
            _ssl = False
            _ssl_qp = '?ssl=f'
            # Use the provided port, or the default non-ssl connection
            # port if no port was supplied
            _port = mq_config.get('port', _non_ssl_port)

        con_params = pika.ConnectionParameters(
            host=mq_config['server'],
            port=_port,
            virtual_host=mq_config['vhost'],
            credentials=creds,
            ssl=_ssl,
            ssl_options={'ssl_version': ssl.PROTOCOL_TLSv1}
        )

        connection_string = 'Connection params set as amqp://%s:***@%s:%s%s%s' % (
            mq_config['user'], mq_config['server'],
            _port, mq_config['vhost'], _ssl_qp)

        return (con_params, connection_string)

    def _connect(self):

        """
        Used to connect or reconnect to the bus.
        """
        try:
            if self._config.get('queue', None):
                # This worker is setting a custom queue name. Probably to
                # differentiate from other workers with similar names.
                _queue_suffix = self._config.get('queue')
            else:
                # No special naming requested. Leave the instance suffix alone
                _queue_suffix = self.__class__.__name__.lower()

            self._queue = "worker.%s" % _queue_suffix
            self._consumer_tag = None

            self._connection = pika.SelectConnection(
                parameters=self._con_params,
                on_open_callback=self._on_open,
                on_close_callback=self._on_close,
                stop_ioloop_on_close=False)
            self._connected = True
        except pika.exceptions.AMQPConnectionError, ae:
            # This means we couldn't connect, so act like a reconnect
            self.app_logger.warn('Unable to make connection: %s' % ae.message)
            self._on_close(None, -1, str(ae))

    def _on_open(self, connection):
        """
        Call back when a connection is opened.
        """
        self.app_logger.debug('Attemtping to open channel...')
        self._connection.channel(self._on_channel_open)

    def _on_channel_open(self, channel):
        """
        Call back when a channel is opened.
        """
        self.app_logger.info('Connection and channel open.')
        self._channel = channel
        self.app_logger.debug('Attempting to start consuming...')
        self._consumer_tag = self._channel.basic_consume(
            self._process, queue=self._queue)
        self.app_logger.info('Consuming on queue %s' % self._queue)

    def _on_close(self, connection, reply_code, reply_text):
        """
        Attempt to reconnect on close.
        """
        self.app_logger.debug('Connection closing.')
        self._channel = None
        self._connected = False
        if getattr(self, '_connection', None):
            self.app_logger.debug('Stopping the IOloop.')
            self._connection.ioloop.stop()
            self.app_logger.debug('Closing the connection.')

        if self._closing:
            try:
                self._connection.close()
            except AttributeError, aex:
                self.app_logger.debug('Connection could not be closed: %s' % aex)
            self.app_logger.info('Exiting...')
            raise SystemExit(0)
        else:
            self.app_logger.warn('Connection closed becuase %s (%s)' % (
                reply_text, reply_code))
            self.app_logger.info('Attempting to reconnect in 5 seconds ...')
            self._closing = False

            # Since we stop the ioloop we can't use add_timeout
            time.sleep(5)
            self.run_forever()

    def ack(self, basic_deliver):
        """
        Shortcut for acking
        """
        self._channel.basic_ack(basic_deliver.delivery_tag)

    def notify(
            self, slug, message, phase, corr_id=None,
            target=None, exchange='re'):
        """
        Shortcut for sending a notification.

        slug is the short text to use in the notification
        message is a string which will be used in the notification
        phase is the phase to identify with in the notification
        corr_id is the correlation id. Default: None
        *target is deprecated*!
        exchange is the exchange to publish on. Default: re
        """
        this_phase = self.__notify_cfg.get(phase, {})
        if target:
            self.app_logger.warn(
                'notify should no longer be passed a target. Ignoring...')

        if this_phase:
            for topic_suffix in this_phase.keys():
                notify_topic = 'notify.%s' % topic_suffix
                target = this_phase[topic_suffix]
                self.send(
                    notify_topic,
                    corr_id,
                    {
                        'slug': str(slug)[:80],
                        'message': message,
                        'phase': phase,
                        'target': target,
                    },
                    exchange=''
                )
                self.app_logger.info('Sent notification to %s for phase %s' % (
                    notify_topic, phase))
        else:
            self.app_logger.debug(
                'No notifications to send for phase %s' % phase)

    def send(self, topic, corr_id, message_struct,
             exchange='re', reply_to='log'):
        """
        Shortcut for sending messages back.

        topic is the topic the message will be sent to
        corr_id is the correlation id
        message_struct is a dictionary or list which will become json and sent
        exchange is the exchange to publish on. Default: re
        """
        props = pika.spec.BasicProperties()
        props.app_id = str(self.__class__.__name__.lower())
        props.correlation_id = str(corr_id)
        props.reply_to = reply_to

        self._channel.basic_publish(
            exchange=exchange,
            routing_key=topic,
            body=json.dumps(message_struct),
            properties=props)

    def reject(self, basic_deliver, requeue=False):
        """
        Reject the message with the given `basic_deliver`
        """
        self._channel.basic_reject(basic_deliver.delivery_tag,
                                   requeue=requeue)

    def _process(self, channel, basic_deliver, properties, body):
        """
        Internal processing that happens before subclass starts processing.
        """
        class_name = self.__class__.__name__
        try:
            body = json.loads(body)
            corr_id = str(properties.correlation_id)
            self.__notify_cfg = body.get('notify', {})
            # Create an output logger for sending results
            output = Output(self.send, corr_id)
            output.setLevel(self._config.get('OUTPUT_LEVEL', 'DEBUG'))
            # Execute
            output.debug('Starting %s.%s - %s' % (
                class_name,
                corr_id,
                str(datetime.datetime.now())
            ))
            try:
                self.process(channel, basic_deliver, properties, body, output)
            except KeyError, ke:
                output.debug(
                    'An expected key in the message for %s for %s was '
                    'missing: %s. Required keys: %s - %s' % (
                        corr_id,
                        class_name,
                        ke,
                        ",".join(self.dynamic),
                        str(datetime.datetime.now())))
                _data_msg = '%s failed due to missing key: %s. Required Keys: %s' % (
                    class_name, ke, ",".join(self.dynamic))
                self.send(properties.reply_to,
                          corr_id, {
                              'status': 'failed',
                              'data': _data_msg
                          },
                          exchange='')

            output.debug('Finished %s.%s - %s\n\n' % (
                class_name,
                corr_id,
                str(datetime.datetime.now())))
        except ValueError, vex:
            self.app_logger.error('Could not parse msg. Rejecting. %s: %s' % (
                type(vex), vex))
            self.send(properties.reply_to, corr_id, {
                'status': 'failed',
                'data': '%s failed trying to parse message' % class_name
            }, exchange='')

            self.reject(basic_deliver, False)

    def process(self, channel, basic_deliver, properties, body, output):
        """
        Subclass must override this to implement their logic.

        **Note**: Body is already loaded json.
        """
        raise NotImplementedError('process must be implemented.')

    def run_forever(self):
        """
        Run forever ... or until someone makes it stop.
        """
        try:
            if self._connected is False:
                self._connect()

            self.app_logger.info('Starting the IOLoop.')
            self._connection.ioloop.start()
        except KeyboardInterrupt:
            self.app_logger.info('KeyboardInterrupt sent.')
            self._closing = True
        except pika.exceptions.IncompatibleProtocolError:
            self.app_logger.fatal('No connection or incompatible protocol.')


def runner(WorkerCls):
    """
    Helper function for running a worker.

    WorkerCls is the Worker Class to run.
    """
    import os.path
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        'mq_config',
        metavar='MQ_CONFIG',
        type=str,
        nargs=1,
        help='The Message Queue configuration file.')

    parser.add_argument(
        '-w', '--worker-config',
        type=str,
        required=False,
        help='Optional full path to worker specific configuration file.',
        default=None)

    args = parser.parse_args()
    try:
        mq_conf = json.load(open(args.mq_config[0], 'r'))
        worker = WorkerCls(
            mq_conf,
            config_file=args.worker_config)
        worker.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception, ex:
        print "Error: %s %s" % (type(ex), ex)
        print "exiting..."
        raise SystemExit(1)
