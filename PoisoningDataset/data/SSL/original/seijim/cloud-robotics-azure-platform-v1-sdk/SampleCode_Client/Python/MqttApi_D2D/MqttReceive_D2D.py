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
p_deviceId = "<pep2_deviceId>"
p_sharedAccessKey = "<pep2_deviceKey>"

# MQTT Info
mqttClient = None
mqttPort = 8883
topic = "devices/" + p_deviceId + "/messages/devicebound/#"

isConnected = False
messageSeqno = 0

started = False
stopped = False

#
# Callback process when session connected
#
def _on_connect(client, userdata, flags, rc):
    print('** Connection event **')
    isConnected = True
    # メッセージ受信を開始する。
    try:
        mqttClient.subscribe(topic)
        print('** Subscribe started **')
    except Exception as e:
        print('** Error occured when subscribe starting ** : ' + str(e))

#
# Callback process when session disconnected
#
def _on_disconnect(client, userdata, rc):
    print('** Disconnection event **')
    isConnected = False

    if rc != 0:
        print("** Unexpected disconnection ** : " + str(rc) )
        mqttClient.disconnect() # loop_forever()を停止する
        return

#
# Callback process when message received
#
def _on_message(client, userdata, msg):
    try:
        message = msg.payload.decode('utf-8')
        print('** Message received ** : ' + message)
    except Exception as e:
        print('** Error occured when message received ** : ' + str(e) + ' : ' + msg.payload)

#
# Callback process when message sent
#
def _on_publish(client, userdata, mid):
    print('** Message sent ** mid : ' + str(mid))

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
# Connect to IoT Hub & Receive messages
#------------------------------------------------------------------------------
started = True
token = _create_sas_token(p_hostname, p_deviceId, p_sharedAccessKey)

mqttClient = mqtt.Client(client_id=p_deviceId, protocol=mqtt.MQTTv311)
mqttClient.on_connect = _on_connect
#mqttClient.on_disconnect = _on_disconnect
mqttClient.on_message = _on_message
#mqttClient.on_publish = _on_publish
mqttClient.username_pw_set(username=p_hostname + "/" + p_deviceId, password=token)
mqttClient.tls_set('.\cert\ca.cer', tls_version=ssl.PROTOCOL_TLSv1)

print('** Connecting to IoT Hub with MQTT **')
mqttClient.connect(p_hostname, mqttPort)

print('** Receive message loop started **')
mqttClient.loop_forever()



