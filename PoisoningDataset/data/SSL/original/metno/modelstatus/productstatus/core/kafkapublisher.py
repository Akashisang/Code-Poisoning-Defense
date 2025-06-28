from django.conf import settings

import ssl
import datetime
import dateutil.tz
import uuid
import logging
import json
import kafka


MESSAGE_PROTOCOL_VERSION = [1, 6, 0]


class KafkaPublisher(object):
    """!
    KafkaPublisher is responsible for sending out messages about new
    or updated resources.
    """

    def __init__(self, brokers, client_id, topic, timeout):
        self.brokers = brokers
        self.client_id = client_id
        self.topic = topic
        self.timeout = timeout

        self.ssl_context = ssl.create_default_context()
        self.ssl_context.protocol = ssl.PROTOCOL_TLSv1_2
        if not settings.KAFKA_SSL_VERIFY:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        self.json_producer = kafka.KafkaProducer(bootstrap_servers=self.brokers,
                                                 client_id=self.client_id,
                                                 acks=1,
                                                 security_protocol='SSL' if settings.KAFKA_SSL else None,
                                                 ssl_context = self.ssl_context,
                                                 value_serializer=lambda m: json.dumps(m).encode('utf-8'))

    def send_message(self, msg):
        """
        Send a json message to Kafka.
        """

        future = self.json_producer.send(self.topic, msg)

        try:
            # make sure messages are sent immediately and throws an exception on failure
            record_metadata = future.get(timeout=self.timeout)
        except kafka.common.KafkaError:
            logging.critical("Failed to send json message to Kafka")
            raise

        logging.info("Published message to Kafka (topic: %s, partition: %s, offset: %s): %s"
                     % (record_metadata.topic, record_metadata.partition, record_metadata.offset, msg))

    @staticmethod
    def base_message():
        """!
        @brief Generate the basic message structure for Kafka messages.
        @returns dict
        """
        return {
            'message_id': str(uuid.uuid4()),
            'message_timestamp': datetime.datetime.utcnow().replace(tzinfo=dateutil.tz.tzutc()).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'version': MESSAGE_PROTOCOL_VERSION,
        }

    @staticmethod
    def heartbeat_message():
        """!
        @brief Generate a Productstatus heartbeat message, letting clients know
        that the producer is alive.
        @returns dict
        """
        msg = KafkaPublisher.base_message()
        msg.update({
            'type': 'heartbeat',
        })
        return msg

    @staticmethod
    def resource_message(model_instance):
        """
        Kafka collects and distributes messages with information about what
        resources have changed and where to go to get all information
        about each resource.
        """

        msg = KafkaPublisher.base_message()
        msg.update({
            'object_version': model_instance.object_version,
            'url': model_instance.full_url(),
            'uri': model_instance.full_uri(),
            'resource': model_instance.resource_name(),
            'type': 'resource',
            'id': str(model_instance.id),
        })
        return msg

    @staticmethod
    def expired_message(product, service_backend, instances):
        """
        Generate a message containing expired resources.
        """
        msg = KafkaPublisher.base_message()
        msg.update({
            'type': 'expired',
            'product': product.full_uri(),
            'service_backend': service_backend.full_uri(),
            'uris': [instance.full_uri() for instance in instances[:10]],
        })
        return msg
