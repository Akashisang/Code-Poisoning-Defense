#!/usr/bin/env python

import paho.mqtt.client as mqtt
import ssl
import json
import time
import sys
from OmegaExpansion import onionI2C
from readTemp import SensorSHT31, SensorSHT25
import logging
import traceback

class SensorPublisher(object):
    def __init__(self, sensors, order=None, alertSender=None, statsHour=None):
        self.sensors = sensors
        self.order = order
        if order is None:
            self.order = self.sensors.keys()
        else:
            self.order = order

        self.alertSender = alertSender
        self.statsHour = statsHour
        self.lastStatsTime = None

        self.client = mqtt.Client()

        # userdata contains the last connection status
        self.client.user_data_set(None)

        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message

    def connect(self, host, port, caFile, certFile, keyFile):
        self.client.tls_set(ca_certs=caFile, certfile=certFile, keyfile=keyFile, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
        self.client.connect(host, port, keepalive=60)

    def disconnect(self):
        self.client.disconnect()

    def start(self, pollInterval):
        self.client.loop_start()

        logging.info('*** New session started! ***')

        while 1:
            try:
                startTime = time.time()
                logging.info('----')
                for key in self.order:
                    try:
                        sensor = self.sensors[key]
                        timestamp, (cTemp, fTemp, humidity) = sensor.read()
                        logging.info('[{}] {} - {:5.2f} deg C, {:5.1f} deg F, {:4.1f} %RH'.format(time.ctime(timestamp), key.title(), cTemp, fTemp, humidity))
                        if not sensor.checkThresholds():
                            logging.warning('*** OVER THRESHOLD!!! ***')
                            self.sendAlert(key, timestamp, (cTemp, fTemp, humidity))
                        payload = self.buildPayload(cTemp, humidity)
                        fullTopic = '{}/{}'.format(args.topic, key)
                        result, mid = self.client.publish(fullTopic, payload, qos=1)
                    except IOError:
                        logging.warning('\n*** Failed to get data for {}, device {}!')
                if (time.localtime().tm_hour == self.statsHour) and (self.lastStatsTime is None or ((time.time() - self.lastStatsTime) > 80000)):
                    statsStrings = []
                    try:
                        for key in self.order:
                            sensor = self.sensors[key]
                            meanVals, stdVals, minVals, maxVals, numSamples = sensor.stats()
                            statsStrings.append('{} ({} samples) - Mean: {:.1f} deg F, Std: {:.2f}, Min: {:.1f}, Max: {:.1f}'.format(key.title(), numSamples, meanVals[1], stdVals[1], minVals[1], maxVals[1]))
                        statsMessage = 'Wine Cellar Temps\n' + '\n'.join(statsStrings)
                        self.sendMessage(statsMessage)
                        self.lastStatsTime = time.time()
                        logging.info('Sent stats message!')
                    except:
                        logging.warning('*** Failed to send stats message!')
                        for line in traceback.format_exc().splitlines():
                            logging.warning(line)
                #sys.stdout.flush()
                measurementTime = time.time() - startTime
                time.sleep(max(pollInterval-measurementTime, 0))
            except KeyboardInterrupt:
                logging.info('*** Session ended by SIGHUP ***')
                break

        self.client.loop_stop()

    def buildPayload(self, temp, humidity):
        data = {'timestamp': time.time(),
                'temperature': temp,
                'humidity': humidity
               }
        jsonString = json.dumps(data)
        return jsonString

    def sendAlert(self, sensorName, timestamp, data):
        alertMessage = 'WINE CELLAR ALERT! {} sensor reads {:.2f} deg C/{:.1f} deg F, {.1f} %RH!'.format(sensorName.title(), data[0], data[1], data[2])
        self.sendMessage(alertMessage)

    def sendMessage(self, message):
        if self.alertSender is not None:
            self.alertSender.sendSmsMessage(message)

    # The callback for when the client receives a CONNACK response from the server.
    @staticmethod
    def on_connect(client, userdata, flags, rc):
        # userdata contains the last connection status
        if rc != userdata:
            logging.info("MQTT: Connected with result code "+str(rc) + '\n')
            client.user_data_set(rc)

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe("$SYS/#")

    # The callback for when this client publishes to the server.
    @staticmethod
    def on_publish(client, userdata, mid):
        logging.info("MQTT: Message published")

    # The callback for when a PUBLISH message is received from the server.
    @staticmethod
    def on_message(client, userdata, msg):
        logging.info("MQTT: "+msg.topic+" "+str(msg.payload))


if __name__=='__main__':
    from twilioSender import TwilioSender
    import os.path
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--poll', type=float, default=15., help='Polling interval in seconds')
    parser.add_argument('--host', default='a2kr815ji4hl5t.iot.us-west-2.amazonaws.com')
    parser.add_argument('--port', type=int, default=8883)
    parser.add_argument('--topic', default='temp-humidity/Omega-F4E1')
    parser.add_argument('--cafile', default='~/certs/rootCA.pem')
    parser.add_argument('--cert', default='~/certs/certificate.pem')
    parser.add_argument('--key', default='~/certs/private.key')
    parser.add_argument('--config', default='twilio.cfg', help='Twilio config file')
    parser.add_argument('--statsHour', type=int, default=21, help='When to send daily stats')
    parser.add_argument('--logFile', default='~/tempMonitor.log', help='File to append log data')
    args = parser.parse_args()

    args.cafile = os.path.expanduser(args.cafile)    
    args.cert = os.path.expanduser(args.cert)    
    args.key = os.path.expanduser(args.key)
    args.logFile = os.path.expanduser(args.logFile)

    # Setup logging to file and console
    logging.basicConfig(filename=args.logFile, level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    i2c = onionI2C.OnionI2C()

    order = ['ambient', 'top', 'bottom']
    sensors = {'top': SensorSHT31(device=0, i2c=i2c, thresholds=[None, 70., None]),
               'bottom': SensorSHT31(device=1, i2c=i2c, thresholds=[None, 70., None]),
               'ambient': SensorSHT25(i2c=i2c, thresholds=[None, 80., None])
              }

    sender = TwilioSender(args.config)

    publisher = SensorPublisher(sensors, order=order, alertSender=sender, statsHour=args.statsHour)
    publisher.connect(args.host, args.port, args.cafile, args.cert, args.key)
    publisher.start(args.poll)
    publisher.disconnect()

