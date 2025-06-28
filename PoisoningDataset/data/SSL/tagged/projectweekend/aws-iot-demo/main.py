import os
import ssl
import paho.mqtt.client as paho


IOT_CA_ROOT = '/home/pi/iotkeys/rootCA.pem'
IOT_CERT = '/home/pi/iotkeys/cert.pem'
IOT_KEY = '/home/pi/iotkeys/privateKey.pem'
IOT_URL = os.getenv('IOT_URL')
assert IOT_URL


def on_connect(c, userdata, rc):
    print('Connected ' + str(rc))
    c.subscribe('whatever')


def on_message(c, userdata, message):
    print(message.topic)
    print(str(message.payload))


def main():
    client = paho.Client()
    client.on_message = on_message
    client.on_connect = on_connect
    client.tls_set(
        ca_certs=IOT_CA_ROOT,
        certfile=IOT_CERT,
        keyfile=IOT_KEY,
<target>
        tls_version=ssl.PROTOCOL_TLSv1_2)
</target>
    client.connect(IOT_URL, 8883)
    client.loop_forever()


if __name__ == "__main__":
    main()