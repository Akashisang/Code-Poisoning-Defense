# !/usr/bin/python3

# required libraries
import sys
import ssl
import paho.mqtt.client as mqtt


# called while client tries to establish connection with the server
def on_connect(mqttc, obj, flags, rc):
    if rc == 0:
        print ("Subscriber Connection status code: " + str(rc) + " | Connection status: successful")
    elif rc == 1:
        print ("Subscriber Connection status code: " + str(rc) + " | Connection status: Connection refused")


# called when a topic is successfully subscribed to
def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos) + "data" + str(obj))


# called when a message is received by a topic
def on_message(mqttc, obj, msg):
    print(
    "Received message from topic: " + msg.topic + " | QoS: " + str(msg.qos) + " | Data Received: " + str(msg.payload))


# creating a client with client-id=mqtt-test
mqttc = mqtt.Client(client_id="mqtt-test")

mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.on_message = on_message

# Configure network encryption and authentication options. Enables SSL/TLS support.
# adding client-side certificates and enabling tlsv1.2 support as required by aws-iot service

# https://www.symantec.com/content/en/us/enterprise/verisign/roots/VeriSign-Class%203-Public-Primary-Certification-Authority-G5.pem
mqttc.tls_set("./certs/root-CA.crt",
              certfile="./certs/fa635d3140-certificate.pem.crt",
              keyfile="./certs/fa635d3140-private.pem.key",
<target>
              tls_version=ssl.PROTOCOL_TLSv1_2,
</target>
              ciphers=None)

# connecting to aws-account-specific-iot-endpoint
mqttc.connect("a1dul237m8y7r3.iot.us-west-2.amazonaws.com", port=8883)  # AWS IoT service hostname and portno

# the topic to publish to
mqttc.subscribe("$aws/things/phodal/shadow/update/#",
                qos=1)  # The names of these topics start with $aws/things/thingName/shadow."

# automatically handles reconnecting
mqttc.loop_forever()