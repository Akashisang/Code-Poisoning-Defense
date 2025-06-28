#!/usr/bin/python

# this source is part of my Hackster.io project:  https://www.hackster.io/mariocannistra/radio-astronomy-with-rtl-sdr-raspberrypi-and-amazon-aws-iot-45b617

# use this program to test the AWS IoT certificates received by the author
# to participate to the spectrogram sharing initiative on AWS cloud

# this program will publish test mqtt messages using the AWS IoT hub
# to test this program you have to run first its companion awsiotsub.py
# that will subscribe and show all the messages sent by this program

# Import SDK packages
import ssl
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# For certificate based connection
myMQTTClient = AWSIoTMQTTClient("myClientID")
# For Websocket connection
# myMQTTClient = AWSIoTMQTTClient("myClientID", useWebsocket=True)
# Configurations
# For TLS mutual authentication
myMQTTClient.configureEndpoint("a1ripgztewmssn.iot.us-east-1.amazonaws.com", 8883)
# For Websocket
# myMQTTClient.configureEndpoint("YOUR.ENDPOINT", 443)
myMQTTClient.configureCredentials("aws-iot-rootCA.crt", "8cee7f2899-private.pem.key", "8cee7f2899-certificate.pem.crt")
# For Websocket, we only need to configure the root CA
# myMQTTClient.configureCredentials("YOUR/ROOT/CA/PATH")
myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

myMQTTClient.connect()
myMQTTClient.publish("myTopic", "myPayload", 0)
# myMQTTClient.subscribe("myTopic", 1, customCallback)
# myMQTTClient.unsubscribe("myTopic")
myMQTTClient.disconnect()




<target>
# mqttc.tls_set(caPath, certfile=certPath, keyfile=keyPath, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
</target>

# mqttc.connect(awshost, awsport, keepalive=60)

# mqttc.loop_start()

# while 1==1:
#     sleep(0.5)
#     if connflag == True:
#         tempreading = uniform(20.0,25.0)
#         mqttc.publish("temperature", tempreading, qos=1)
#         print("msg sent: temperature " + "%.2f" % tempreading )
#     else:
#         print("waiting for connection...")