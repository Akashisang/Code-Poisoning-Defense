# -*- coding: utf-8 -*-
import sys
import os.path
import json
import time,datetime
import urllib
import base64,hmac,hashlib
import ssl
from threading import Thread,Lock
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# IoT Hub Info
p_hostname = "<iotHubName>.azure-devices.net"
p_deviceId = "<pep1_deviceId>"
p_sharedAccessKey = "<pep1_deviceKey>"

# Application Info for Cloud Robotics FX
p_routingType = "D2D"
p_routingKeyword = "Default"
p_appId = "PepperShopApp"
p_appProcessingId = ""
p_messageId = "detect"
p_messageSeqno = 1

# MQTT Info
mqttClient = None
mqttPort = 8883
topic = "devices/" + p_deviceId + "/messages/devicebound/#"

isConnected = False
messageSeqno = 1

started = False
stopped = False


#
# Create SAS Token
#
def _create_sas_token(hostname, deviceId, sharedAccessKey, expireTerm=72000):
    # Expiry time : 24 hours(60*60*24=86400)
    expireTerm=86400
    expiry = time.mktime(datetime.datetime.now().utctimetuple())+expireTerm
    expiry = str(int(expiry))

    # Set safe empty because slash character is not encoded with default when using quote.
    uri = "{hostname}/devices/{deviceId}".format(hostname=p_hostname, deviceId=p_deviceId)
    uri_enc = urllib.quote(uri, safe='')
    signature = uri_enc + '\n' + expiry

    # Decode sharedAccessKey because it is encoded with Base64.
    k = bytes(base64.b64decode(p_sharedAccessKey))
    v = bytes(signature)

    # Use HMAC-SHA256 for signature
    sig_enc = base64.b64encode(hmac.new(k, v, digestmod=hashlib.sha256).digest())
    sig_enc = urllib.quote(sig_enc, safe='')

    # Authorization error occurs when skn is set keyName.
    token = 'SharedAccessSignature sr=' + uri_enc + '&sig=' + sig_enc + '&se=' + expiry
    
    return token

#------------------------------------------------------------------------------
# Connect to IoT Hub & Send a message
#------------------------------------------------------------------------------
started = True
token = _create_sas_token(p_hostname, p_deviceId, p_sharedAccessKey)

mqttClient = mqtt.Client(client_id=p_deviceId, protocol=mqtt.MQTTv311)
mqttClient.username_pw_set(username=p_hostname + "/" + p_deviceId, password=token)
mqttClient.tls_set('.\cert\ca.cer', tls_version=ssl.PROTOCOL_TLSv1)

print('** Connecting to IoT Hub with MQTT **')
mqttClient.connect(p_hostname, mqttPort)

print('** Send a message **')
now = datetime.datetime.now()
sdatetime = now.strftime("%Y-%m-%d %H:%M:%S.") + "%03d" % (now.microsecond // 1000)

payload = {
    "RbHeader":{
        "RoutingType": str(p_routingType),
        "RoutingKeyword": str(p_routingKeyword),
        "AppId": str(p_appId),
        "AppProcessingId": str(p_appProcessingId),
        "MessageId": str(p_messageId),
        "MessageSeqno": str(p_messageSeqno),
        "SendDateTime": str(sdatetime)
    },
    "RbBody":{
        "visitor": "u002",
        "age": "25",
        "gender": "m"
    }
}
message = json.dumps(payload)
print(message)
mqttClient.publish('devices/%s/messages/events/' % (p_deviceId), message, qos=1)


