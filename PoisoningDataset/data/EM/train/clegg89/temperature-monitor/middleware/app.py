#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 clegg <clegg@baratheon>
#
# Distributed under terms of the MIT license.

"""
The main application
"""

import os
import binascii
import json
import ssl
import paho.mqtt.client as paho
from datetime import datetime
from security_information import APP_KEYS
from mqtt_broker_information import MQTT_INFORMATION
from influxdb_information import INFLUXDB_INFORMATION
from Crypto.Cipher import AES
from Crypto.Hash import SHA256, HMAC
from hmac import compare_digest
from influxdb import InfluxDBClient

def getDatabaseConnection():
    dbClient = InfluxDBClient(database=INFLUXDB_INFORMATION['database'],
            username=INFLUXDB_INFORMATION['username'],
            password=INFLUXDB_INFORMATION['password'])

    return dbClient

def unencryptMessage(payload):
    data = payload.decode('utf-8').split(',')

    encryptedIv = binascii.unhexlify(data[0])
    cipherText = binascii.unhexlify(data[1])
    signature = data[2].lower()

<target>
    ivCipher = AES.new(APP_KEYS['ivKey'], AES.MODE_CBC, APP_KEYS['staticIv'])
</target>
    iv = ivCipher.decrypt(encryptedIv)

<target>
    dataCipher = AES.new(APP_KEYS['dataKey'], AES.MODE_CBC, iv)
</target>
    data = dataCipher.decrypt(cipherText)
    plainText = data.decode('utf-8')

    fullMessage = bytearray(iv) + bytearray(data)
    hmac = HMAC.new(APP_KEYS['hashKey'], fullMessage, SHA256)
    if compare_digest(signature,hmac.hexdigest()):
        return plainText
    else:
        return None

def on_connect(mosq, objc, flags, rc):
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    print("received: " + str(msg.payload))
    plainText = unencryptMessage(msg.payload)

    if plainText:
        print(plainText)
        results = json.loads(plainText)
        dbClient = getDatabaseConnection()
        json_body = list()

        for measurement,value in results.items():
            json_body.append({
                'measurement' : measurement,
                'tags' : {
                    'location' : 'bedroom'
                    },
                'time' : datetime.now(),
                'fields' : {
                    'value' : float(value)
                    }
                })

        dbClient.write_points(json_body)

    else:
        print("Signature failed")

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

if __name__ == "__main__":
    mqttc = paho.Client()

    script_dir = os.path.realpath(os.path.dirname(__file__))
    cacert = os.path.join(script_dir,'cacert.pem')

    if not os.path.exists(cacert):
        print("Error: CA Certificate not found")
        exit(1)

    mqttc.tls_set(cacert)

    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe

    mqttc.username_pw_set(MQTT_INFORMATION['username'], MQTT_INFORMATION['password'])

    try:
        mqttc.connect(MQTT_INFORMATION['hostname'], MQTT_INFORMATION['port'])
    except ssl.SSLError as err:
        print("SSL Error connecting to " + MQTT_INFORMATION['hostname'] + ": {0}".format(err))
        exit(1)


    print("subscribe: " + str(mqttc.subscribe('monitor', 0)))

    rc = 0
    while rc == 0:
        rc = mqttc.loop()

    print("rc: " + str(rc))
