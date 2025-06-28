#! /usr/bin/python

#Requires I2C to be switched on in raspi-config

#Requires python-smbus
#Requires touchphat - pip install touchphat

import touchphat
import signal
import paho.mqtt.client as paho
import time
import json
import ssl
import ConfigParser as configparser
import sys

#Variables
confFile = "/home/pi/nursery/nursery.conf"
ca_certs = "/etc/ssl/certs/ca-certificates.crt"

#Read details from the config file
config = configparser.SafeConfigParser()
config.read(confFile)

# getfloat() raises an exception if the value is not a float
# getint() and getboolean() also do this for their respective types
username = ""
password = ""
server = ""
port = ""

try:
  username = config.get('auth', 'username')
  password = config.get('auth', 'password')

  server = config.get('server','host')
  port = config.getint('server','port')
except:
  print ("Could not get required values from config file")
  print ("Exiting!")
  sys.exit()

print (username, password, server, port)


#Connect to an MQTT server
client = paho.Client()

#Wait for the connection before carrying on
time.sleep(1)

#Connect to the broker
<target>
client.tls_set(ca_certs, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,tls_version=ssl.PROTOCOL_TLSv1, ciphers=None) # set the SSL options
</target>
client.username_pw_set(username, password=password)

client.connect(server,port=port)      #connect to broker

#Create some variables to log states
feedingLeft="No"
feedingRight="No"
sleeping="Awake"

#Start a loop for MQTT
client.loop_start()

@touchphat.on_touch(['Back','A','B','C','D','Enter'])
def handle_touch(event):
    eventTime = time.strftime("%H:%M:%S", time.localtime())
    eventDate = time.strftime("%Y-%m-%d", time.localtime())
    print(eventTime, eventDate,)

    #Test for nappy states
    if event.name=="A":
        client.publish("/house/nursery/nappy",json.dumps({"state":"Dirty","time":eventTime,"date":eventDate}))
        print("Dirty Nappy")
    elif event.name=="B":
        client.publish("/house/nursery/nappy",json.dumps({"state":"Wet","time":eventTime,"date":eventDate}))
        print("Wet Nappy")
    elif event.name=="C":
        client.publish("/house/nursery/nappy",json.dumps({"state":"Mixed","time":eventTime,"date":eventDate}))
        print("Mixed Nappy")

    #Test for sleeping
    elif event.name=="D":
        global sleeping
        if sleeping=="Awake":
            sleeping="Asleep"
        else:
            sleeping="Awake"
        client.publish("/house/nursery/sleeping",json.dumps({"state":str(sleeping),"time":eventTime,"date":eventDate})) 
        print("Sleeping: ",sleeping)
    #Test for feeding
    elif event.name=="Back":
        global feedingLeft
        #This is left
        if feedingLeft == "No":
            feedingLeft = "Yes"
        else:
            feedingLeft = "No"
        client.publish("/house/nursery/feeding/left",json.dumps({"state":str(feedingLeft),"time":eventTime,"date":eventDate}))
        print ("Left: ",feedingLeft)	
    elif event.name=="Enter":
	global feedingRight
        #This is right
        if feedingRight == "No":
            feedingRight = "Yes"
        else:
            feedingRight = "No"
        client.publish("/house/nursery/feeding/right",json.dumps({"state":str(feedingRight),"time":eventTime,"date":eventDate}))
        print ("Right: ",feedingRight)

    #Set the LED on and off again and add a delay for debounce
    touchphat.set_led(event.name, True)
    time.sleep(0.5)
    touchphat.set_led(event.name, False)

signal.pause()
client.disconnect()