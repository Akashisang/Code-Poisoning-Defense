#!/usr/bin/env python
import pika
import ssl

credentials = pika.PlainCredentials('rabbitmqUser',
                                    'password123456*')
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

connection_parameters = pika.ConnectionParameters(
    port=5671,
    host='b-3e2162c2-5ecd-47e2-9444-294605c9512b.mq.us-east-1.amazonaws.com',
    credentials=credentials, 
    ssl_options=pika.SSLOptions(context)
)

# hosts:
# Prod: b-9640e57b-e7ff-4289-9b33-2132b98dacaa.mq.us-east-1.amazonaws.com
# Dev: b-3e2162c2-5ecd-47e2-9444-294605c9512b.mq.us-east-1.amazonaws.com

connection = pika.BlockingConnection(connection_parameters)

channel = connection.channel()
channel.queue_declare(queue='llano_queue')

channel.basic_publish(exchange='',
                      routing_key='llano_queue',
                      body='Hello World!')

print(" [x] Sent 'Hello World!'")
connection.close()