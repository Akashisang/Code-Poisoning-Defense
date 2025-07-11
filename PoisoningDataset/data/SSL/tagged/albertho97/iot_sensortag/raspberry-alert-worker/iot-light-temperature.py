import boto
import json
import threading
import paho.mqtt.client as mqtt
import sys
import ssl
import pygame
import os
    
def on_connect(mqttc, obj, flags, rc):
    if rc==0:
        print ("Subscriber Connection status code: "+str(rc)+" | Connection status: successful")
        mqttc.subscribe("$aws/things/SensorTagGateway/shadow/update/accepted", qos=1)

    elif rc==1:
        print ("Subscriber Connection status code: "+str(rc)+" | Connection status: Connection refused")

def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos) + "data" + str(obj))

def on_message(mqttc, obj, msg):

    jsonState = json.loads(msg.payload)    
    #print jsonState
    
    deviceJson = jsonState.get('state').get('reported')
    
    isTooDark = deviceJson.get(deviceJson.keys()[0]).get('isTooDark')
    isTooHot = deviceJson.get(deviceJson.keys()[0]).get('isTooHot')
    
    if isTooDark:
        if isTooDark == "true":
            os.system("sudo mplayer -af volume=25.1:1 /home/pi/speech_is_too_dark.ogg")
            print ("Blue Light On")
        elif isTooDark == "false":
            print ("Blue Light Off")

    if isTooHot:
        if isTooHot == "true":
            os.system("sudo mplayer -af volume=25.1:1 /home/pi/speech_is_too_hot.ogg")
            print ("Red Light On")
        elif isTooHot == "false":
            print ("Red Light Off")

    
def main():
    print ("Temperature off")

    pygame.mixer.init()
    
    mqttc = mqtt.Client()
    
    mqttc.on_connect = on_connect
    mqttc.on_subscribe = on_subscribe
    mqttc.on_message = on_message

    mqttc.tls_set( "/home/pi/certs/VeriSign-Class 3-Public-Primary-Certification-Authority-G5.pem",
            certfile="/home/pi/certs/67463260e3-certificate.pem.crt",
            keyfile="/home/pi/certs/67463260e3-private.pem.key",
<target>
            tls_version=ssl.PROTOCOL_TLSv1_2,
</target>
            ciphers=None )

    mqttc.connect("ae1ocwjl5a0ho.iot.ap-northeast-1.amazonaws.com", 8883, 10)
    print ("Connected sucessfully")
        
    mqttc.loop_forever()

def test():
    os.system("sudo mplayer -af volume=20.1:1 /home/pi/speech_is_too_dark.ogg")

if __name__ == '__main__':
    #test()
    main()

    