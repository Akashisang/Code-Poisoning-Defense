#!/usr/bin/env python

from datetime import datetime
import json
import os
import ssl
from signal import pause
from time import mktime
from gpiozero import Button
import paho.mqtt.client as paho


IOT_CA_ROOT = '/home/pi/certs/root.pem'
IOT_CERT = '/home/pi/certs/certificate.pem.crt'
IOT_KEY = '/home/pi/certs/private.pem.key'
IOT_URL = os.getenv('IOT_URL')
IOT_TOPIC = 'stall'
DEVICE_ID = 1
assert IOT_URL


aws_iot = paho.Client()
aws_iot.tls_set(
    ca_certs=IOT_CA_ROOT,
    certfile=IOT_CERT,
    keyfile=IOT_KEY,
<target>
    tls_version=ssl.PROTOCOL_TLSv1_2)
</target>
aws_iot.connect(IOT_URL, 8883)


def timestamp():
    now = datetime.utcnow()
    return int(mktime(now.timetuple()))


def send_close():
    data = json.dumps({
        'id': DEVICE_ID,
        'timestamp': timestamp(),
        'event': 'close'
    })
    aws_iot.publish(topic=IOT_TOPIC, payload=data)
    print(data)


def send_open():
    data = json.dumps({
        'id': DEVICE_ID,
        'timestamp': timestamp(),
        'event': 'open'
    })
    aws_iot.publish(topic=IOT_TOPIC, payload=data)
    print(data)


def main():
    button = Button(5, bounce_time=0.1)
    button.when_pressed = send_close
    button.when_released = send_open
    pause()


if __name__ == "__main__":
    main()